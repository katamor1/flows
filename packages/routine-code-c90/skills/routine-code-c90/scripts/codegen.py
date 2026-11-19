"""Data-only C90 job preparation, generation provenance and host verification."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT.parents[1]
VERSION = '0.2.0'
PAYLOAD_ROOTS = ('scripts/', 'references/', 'assets/templates/', 'assets/examples/')
SAFE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z')
C_ID = re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')
SHA256 = re.compile(r'[0-9a-f]{64}\Z')
FLAGS = ['-std=c90', '-pedantic-errors', '-Wall', '-Wextra', '-Werror']
PROFILE_FIELDS = {'name', 'target', 'headers', 'test_sources', 'support_sources',
                  'defines', 'allowed_undefined_symbols', 'allowed_public_symbols'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(content):
    return hashlib.sha256(content).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def write_new(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as output:
        output.write(content)


def save_new(path, value):
    write_new(path, json_bytes(value))


@contextmanager
def owned_guard(path):
    try:
        handle = path.open('x')
    except FileExistsError:
        raise ValueError('Job is busy; existing job lock: ' + str(path)) from None
    try:
        with handle:
            yield
    finally:
        path.unlink()


def validate_relative(relative):
    require(isinstance(relative, str) and relative and '\\' not in relative
            and ':' not in relative, 'Invalid job-relative path')
    require(not Path(relative).is_absolute() and '..' not in Path(relative).parts,
            'Path escapes job root')


def safe_path(base, relative):
    base = base.resolve()
    validate_relative(relative)
    path = base / relative
    require(not Path(relative).is_absolute() and '..' not in Path(relative).parts
            and path.resolve().is_relative_to(base), 'Path escapes job root')
    current = path
    while current != base:
        require(not current.is_symlink() and not current.is_junction(),
                'Links/junctions are unsupported in jobs')
        current = current.parent
    return path


def package_inventory():
    return {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
            if p.is_file() and (p.relative_to(ROOT).as_posix() in {'SKILL.md', '.gitattributes'}
            or p.relative_to(ROOT).as_posix().startswith(PAYLOAD_ROOTS))}


def doctor():
    release = load(ROOT / 'release.json')
    require(release.get('version') == VERSION, 'Package release version mismatch; reseal the 0.2.0 package')
    require(package_inventory() == set(release['files']), 'Package inventory mismatch')
    for name, sha in release['files'].items():
        require(digest(safe_path(ROOT, name).read_bytes()) == sha,
                'Package resource changed: ' + name)
    require(sys.version_info[:2] == (3, 12), 'This release is verified with Python 3.12')
    return release, digest((ROOT / 'release.json').read_bytes())


def job_path(args):
    require(SAFE_ID.fullmatch(args.job), 'Invalid job ID')
    workspace = args.workspace.expanduser().resolve()
    require(not workspace.is_relative_to(BUNDLE), 'Jobs must be outside the package')
    return workspace, safe_path(workspace, args.job)


def validate_spec(content):
    spec = json.loads(content.decode('utf-8'))
    require(isinstance(spec, dict), 'Specification must be a JSON object')
    document, interface = spec.get('document', {}), spec.get('interface', {})
    require(isinstance(document, dict) and isinstance(interface, dict), 'Invalid specification sections')
    for name in ('id', 'routine_id', 'routine_name', 'status'):
        require(isinstance(document.get(name), str) and document[name].strip(), 'Missing document.' + name)
    routine = document['routine_name']
    require(C_ID.fullmatch(routine), 'document.routine_name must be a C identifier')
    require(interface.get('language') == 'C90', 'interface.language must be C90')
    require(isinstance(interface.get('type_definitions'), str), 'interface.type_definitions must be a string (empty is supported)')
    prototype = interface.get('prototype')
    clean = re.sub(r'/\*.*?\*/|//[^\n]*', '', prototype, flags=re.S) if isinstance(prototype, str) else ''
    require(clean.strip().endswith(';')
            and re.search(r'\b' + re.escape(routine) + r'\s*\(', clean),
            'interface.prototype must declare document.routine_name and end with a semicolon')
    return spec


def string_list(value, field):
    require(isinstance(value, list) and all(isinstance(item, str) and item for item in value),
            'Profile ' + field + ' must be a string list')
    require(len(value) == len(set(value)), 'Duplicate profile ' + field)
    return value


def profile_assets(path, routine, spec_sha):
    content = path.read_bytes()
    profile = json.loads(content.decode('utf-8'))
    require(isinstance(profile, dict) and PROFILE_FIELDS <= set(profile)
            and set(profile) <= PROFILE_FIELDS | {'format_version'}, 'Invalid profile fields; executable commands are not supported')
    require(profile.get('format_version', VERSION) == VERSION, 'Unsupported profile version')
    require(isinstance(profile['name'], str) and profile['name'].strip(), 'Profile name is required')
    require(profile['target'] == {'routine_name': routine, 'spec_sha256': spec_sha},
            'Verification profile target does not match routine_name/spec_sha256')
    require(isinstance(profile['headers'], list), 'Profile headers must be a list')
    assets = {'input/verification-profile.json': content}
    headers, tests, support = [], [], []

    def copy_asset(source_name, destination):
        require(isinstance(source_name, str) and source_name, 'Profile source path is required')
        source = Path(source_name).expanduser()
        if not source.is_absolute():
            source = path.parent / source
        source = source.resolve(strict=True)
        require(source.is_file(), 'Profile source is not a file: ' + str(source))
        validate_relative(destination)
        require(destination.casefold() not in {item.casefold() for item in assets}, 'Duplicate profile target: ' + destination)
        data = source.read_bytes()
        data.decode('utf-8')
        assets[destination] = data

    for header in profile['headers']:
        require(isinstance(header, dict) and set(header) == {'source', 'target'}, 'Invalid profile header entry')
        target = header['target']
        require(isinstance(target, str) and target and not target.startswith('include/'), 'headers.target must be relative to include/')
        destination = 'include/' + target
        require(destination.casefold() != ('include/' + routine + '.h').casefold(), 'Profile header collides with generated routine header')
        copy_asset(header['source'], destination)
        headers.append(destination)
    for field, directory, output in (('test_sources', 'tests', tests), ('support_sources', 'support', support)):
        for index, source_name in enumerate(string_list(profile[field], field)):
            basename = Path(source_name).name
            require(Path(basename).suffix.lower() == '.c', 'Profile C source must have a .c filename')
            destination = directory + '/profile-' + str(index).zfill(3) + '-' + basename
            copy_asset(source_name, destination)
            output.append(destination)
    require(all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:=[^\r\n]*)?', item)
                for item in string_list(profile['defines'], 'defines')), 'Profile defines must be C macro definitions, not compiler options')
    guard = 'ROUTINE_CODE_' + routine.upper() + '_H'
    require(all(item.split('=', 1)[0] != guard for item in profile['defines']),
            'Profile define would disable the generated header guard: ' + guard)
    for field in ('allowed_undefined_symbols', 'allowed_public_symbols'):
        require(all(C_ID.fullmatch(item) for item in string_list(profile[field], field)), 'Invalid profile symbol name')
    return profile, assets, headers, tests, support


def publish_stage(stage, destination):
    for attempt in range(20):
        require(not destination.exists(), 'Output appeared during preparation')
        try:
            stage.rename(destination)
            return
        except PermissionError as exc:
            if getattr(exc, 'winerror', None) not in (5, 32) or attempt == 19:
                raise
            time.sleep(0.1)


def prepare(args, release, release_sha):
    spec_path = args.spec.expanduser().resolve(strict=True)
    content = spec_path.read_bytes()
    spec = validate_spec(content)
    document, interface = spec['document'], spec['interface']
    routine, spec_sha = document['routine_name'], digest(content)
    assets = {'input/spec.json': content,
              '.gitattributes': (ROOT / 'assets/templates/job.gitattributes').read_bytes()}
    profile, headers, tests, support = None, [], [], []
    if args.verification_profile is not None:
        profile, copied, headers, tests, support = profile_assets(args.verification_profile.expanduser().resolve(strict=True), routine, spec_sha)
        assets.update(copied)
    template = (ROOT / 'assets/templates/routine.h.tpl').read_text(encoding='utf-8')
    substitutions = {'HEADER_GUARD': 'ROUTINE_CODE_' + routine.upper() + '_H',
                     'TYPE_DEFINITIONS': interface['type_definitions'], 'PROTOTYPE': interface['prototype']}
    header = re.sub(r'\{\{(HEADER_GUARD|TYPE_DEFINITIONS|PROTOTYPE)\}\}',
                    lambda match: substitutions[match[1]], template)
    assets['include/' + routine + '.h'] = header.encode('utf-8')
    config = {'format_version': VERSION, 'spec': 'input/spec.json', 'spec_sha256': spec_sha,
              'header': 'include/' + routine + '.h', 'source': 'src/' + routine + '.c',
              'routine_id': document['routine_id'], 'routine_name': routine,
              'profile': 'input/verification-profile.json' if profile else None,
              'tests': tests, 'support_sources': support, 'headers': headers,
              'defines': profile['defines'] if profile else [],
              'allowed_undefined_symbols': profile['allowed_undefined_symbols'] if profile else [],
              'allowed_public_symbols': profile['allowed_public_symbols'] if profile else [routine]}
    workspace, job = job_path(args)
    workspace.mkdir(parents=True, exist_ok=True)
    with owned_guard(safe_path(workspace, '.' + args.job + '.lock')):
        stage = None
        try:
            require(not job.exists(), 'Job already exists; choose a new job ID')
            stage = Path(tempfile.mkdtemp(prefix='.' + args.job + '-', dir=workspace)).resolve()
            for name, data in assets.items():
                write_new(safe_path(stage, name), data)
            for name in ('src', 'records', 'qa'):
                (stage / name).mkdir()
            save_new(stage / 'job.json', {**config, 'generation_record': 'records/pending.json'})
            save_new(stage / 'package-lock.json', {'format_version': VERSION, 'release_sha256': release_sha,
                     'job_contract': config, 'files': {name: digest(data) for name, data in sorted(assets.items())}})
            save_new(stage / 'input-origin.json', {'source_path': str(spec_path), 'source_sha256': spec_sha,
                     'canonical_copy': 'input/spec.json', 'verification_profile_source': str(args.verification_profile.resolve()) if profile else None})
            publish_stage(stage, job)
            stage = None
        finally:
            if stage is not None and stage.exists():
                require(stage.parent == workspace and stage.name.startswith('.' + args.job + '-'), 'Invalid cleanup path')
                shutil.rmtree(stage)
    return {'status': 'prepared', 'job': str(job), 'source_to_generate': str(job / config['source']),
            'source': str(job / config['source']), 'header': str(job / config['header']),
            'implementation_included': False, 'verification_profile': config['profile']}


def checked_job(job, release_sha):
    config = load(safe_path(job, 'job.json'))
    require(config.get('format_version') == VERSION,
            'Legacy job 0.1.0 is unsupported by 0.2.0; preserve it and its old ZIP, then prepare a new job from the original specification and an explicit verification profile')
    lock = load(safe_path(job, 'package-lock.json'))
    require(lock.get('format_version') == VERSION and lock.get('release_sha256') == release_sha,
            'Job package lock mismatch; use the matching sealed package or prepare a new job')
    require({key: value for key, value in config.items() if key != 'generation_record'} == lock['job_contract'], 'Job contract changed')
    require(isinstance(config.get('generation_record'), str)
            and re.fullmatch(r'records/[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.json', config['generation_record']), 'Invalid generation record path')
    required = {'.gitattributes', config['spec'], config['header'], *config['tests'], *config['support_sources'], *config['headers']}
    if config['profile']:
        required.add(config['profile'])
    require(set(lock['files']) == required, 'Job asset lock inventory mismatch')
    for name, sha in lock['files'].items():
        require(isinstance(sha, str) and SHA256.fullmatch(sha)
                and digest(safe_path(job, name).read_bytes()) == sha, 'Fixed job asset changed: ' + name)
    require(digest(safe_path(job, config['spec']).read_bytes()) == config['spec_sha256'], 'Specification hash changed')
    return config, lock


def record(args, release, release_sha):
    workspace, job = job_path(args)
    require(SAFE_ID.fullmatch(args.generation), 'Invalid generation ID')
    require(args.agent.strip() and args.agent_version.strip() and args.note.strip(), 'Generation provenance must be explicit')
    require(args.bob_executed != 'yes' or 'bob' in args.agent.lower(), 'Bob execution declaration conflicts with agent name')
    with owned_guard(safe_path(workspace, '.' + args.job + '.lock')):
        config, lock = checked_job(job, release_sha)
        safe_path(job, config['source']).read_text(encoding='utf-8')
        mapping = safe_path(job, 'traceability.md')
        require(mapping.is_file() and mapping.stat().st_size > 0, 'Create traceability.md before recording this generation')
        paths = set(lock['files']) | {config['source'], 'traceability.md'}
        files = {name: digest(safe_path(job, name).read_bytes()) for name in sorted(paths)}
        require(all(files[name] == sha for name, sha in lock['files'].items()), 'Fixed job asset changed while recording')
        value = {'format_version': VERSION, 'time_utc': datetime.now(timezone.utc).isoformat(),
                 'agent': args.agent, 'agent_version': args.agent_version, 'bob_executed': args.bob_executed == 'yes',
                 'status': 'draft_trial', 'input_spec_sha256': files[config['spec']], 'header_sha256': files[config['header']],
                 'source_sha256': files[config['source']], 'traceability_sha256': files['traceability.md'],
                 'file_hashes': files, 'release_sha256': release_sha, 'note': args.note,
                 'test_authorship': 'Profile-supplied tests; authorship and specification coverage require independent review.'}
        path = safe_path(job, 'records/' + args.generation + '.json')
        save_new(path, value)
        config['generation_record'] = path.relative_to(job).as_posix()
        pending = safe_path(job, '.job-update-' + args.generation + '.json')
        save_new(pending, config)
        os.replace(pending, job / 'job.json')
    return {'status': 'recorded', 'record': str(path), 'source_sha256': value['source_sha256']}


def command(argv, outdir, label, records, cwd):
    argv = [str(item) for item in argv]
    entry = {'step': label, 'argv': argv, 'cwd': str(cwd), 'returncode': None}
    records.append(entry)
    stdout, stderr = '', ''
    try:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=120, shell=False)
        stdout, stderr = result.stdout, result.stderr
        entry['returncode'] = result.returncode
        return result
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = exc.stdout or b'', exc.stderr or b''
        stdout = stdout.decode('utf-8', 'replace') if isinstance(stdout, bytes) else stdout
        stderr = stderr.decode('utf-8', 'replace') if isinstance(stderr, bytes) else stderr
        entry['error'] = 'timeout after 120 seconds'
        raise RuntimeError(label + ' timed out') from exc
    except OSError as exc:
        entry['error'] = str(exc)
        raise
    finally:
        write_new(outdir / (label + '.stdout.txt'), stdout.encode('utf-8'))
        write_new(outdir / (label + '.stderr.txt'), stderr.encode('utf-8'))


def inspect_dependencies(depfile, snapshot, expected):
    # -MT avoids drive-letter colons in the make target. Parse make escaping.
    text = depfile.read_text(encoding='utf-8').replace('\\\n', '')
    require(text.startswith('routine-object:'), 'Unexpected compiler dependency format')
    words, word, escaped = [], '', False
    remainder = text[len('routine-object:'):]
    for index, character in enumerate(remainder):
        if escaped:
            word += character
            escaped = False
        elif character == '\\':
            # clang on Windows emits native separators verbatim; only make
            # escapes before whitespace/# are escapes on that platform.
            following = remainder[index + 1:index + 2]
            if os.name == 'nt' and following and not following.isspace() and following != '#':
                word += character
            else:
                escaped = True
        elif character.isspace():
            if word:
                words.append(word)
                word = ''
        else:
            word += character
    if word:
        words.append(word)
    for name in words:
        path = Path(name.replace('$$', '$'))
        path = path.resolve() if path.is_absolute() else (snapshot / path).resolve()
        require(path.is_relative_to(snapshot), 'Unfrozen external include dependency: ' + str(path))
        relative = path.relative_to(snapshot).as_posix()
        require(relative in expected and digest(path.read_bytes()) == expected[relative], 'Unrecorded/changed compile dependency: ' + relative)


def verify(args, release, release_sha):
    workspace, job = job_path(args)
    require(SAFE_ID.fullmatch(args.run), 'Invalid run ID')
    with owned_guard(safe_path(workspace, '.' + args.job + '.lock')):
        outdir = safe_path(job, 'qa/' + args.run)
        require(job.is_dir(), 'Job does not exist')
        outdir.mkdir(parents=True, exist_ok=False)
        report = {'format_version': VERSION, 'time_utc': datetime.now(timezone.utc).isoformat(),
                  'kind': 'host_verification', 'status': 'failed',
                  'scope': 'C90 host O0/O2 only; target RTOS, DLL ABI, WCET and Bob IDE execution are not verified',
                  'release_sha256': release_sha, 'files': {}, 'snapshot_files': {}, 'tools': {},
                  'commands': [], 'optimization_results': {}, 'test_execution': 'not_run'}
        try:
            config, lock = checked_job(job, release_sha)
            if not config['tests']:
                report['test_execution'] = 'not_provided'
            record_path = safe_path(job, config['generation_record'])
            generation = load(record_path)
            require(generation.get('format_version') == VERSION and generation.get('release_sha256') == release_sha
                    and generation.get('status') == 'draft_trial', 'Generation identity mismatch')
            required = set(lock['files']) | {config['source'], 'traceability.md'}
            require(set(generation['file_hashes']) == required, 'Generation file hash inventory mismatch')
            aliases = {'input_spec_sha256': config['spec'], 'source_sha256': config['source'],
                       'header_sha256': config['header'], 'traceability_sha256': 'traceability.md'}
            require(all(generation.get(key) == generation['file_hashes'][name] for key, name in aliases.items()), 'Generation hash fields disagree')
            snapshot = outdir / 'snapshot'
            files = {name: safe_path(job, name).read_bytes() for name in sorted(required)}
            for name, data in files.items():
                require(digest(data) == generation['file_hashes'][name], 'Generation record hash mismatch/source changed; record a new generation: ' + name)
                if name in lock['files']:
                    require(digest(data) == lock['files'][name], 'Fixed job asset changed: ' + name)
            files[config['generation_record']] = record_path.read_bytes()
            files['job.json'] = safe_path(job, 'job.json').read_bytes()
            files['package-lock.json'] = safe_path(job, 'package-lock.json').read_bytes()
            require(json.loads(files[config['generation_record']]) == generation
                    and json.loads(files['job.json']) == config
                    and json.loads(files['package-lock.json']) == lock, 'Job metadata changed during snapshot')
            files['verifier-used.py'] = Path(__file__).read_bytes()
            probe_name = 'verifier-interface-probe.c'
            probe_identifier = 'RoutineCode_InterfaceProbe_' + config['spec_sha256'][:16]
            namespace = files[config['header']].decode('utf-8') + '\n' + '\n'.join(config['defines']) + '\n' + config['routine_name']
            while re.search(r'\b' + re.escape(probe_identifier) + r'\b', namespace):
                probe_identifier += '_'
            files[probe_name] = ('typedef char ' + probe_identifier
                                 + '[(sizeof(&' + config['routine_name'] + ') > 0) ? 1 : -1];\n').encode('utf-8')
            for name, data in files.items():
                write_new(safe_path(snapshot, name), data)
            report['generation'] = generation
            report['files'] = {name: digest(data) for name, data in files.items()}
            report['snapshot_files'] = dict(report['files'])
            require(args.clang.is_absolute(), '--clang must be an absolute executable path')
            clang = args.clang.resolve(strict=True)
            nm = clang.with_name('llvm-nm.exe' if os.name == 'nt' else 'llvm-nm')
            require(clang.is_file() and nm.is_file(), 'llvm-nm must be beside the specified Clang executable')
            records = report['commands']
            for label, tool in (('compiler', clang), ('nm', nm)):
                version = command([tool, '--version'], outdir, label + '-version', records, snapshot)
                require(version.returncode == 0, label + ' version command failed')
                report['tools'][label] = {'path': str(tool), 'sha256': digest(tool.read_bytes()), 'version': version.stdout.strip()}
            compile_flags = [*FLAGS, '-x', 'c', '-I', str(snapshot / 'include')]
            for define in config['defines']:
                compile_flags.extend(['-D', define])
            safe_path(snapshot, config['source']).read_text(encoding='utf-8')
            probe_depfile = outdir / 'interface-probe.d'
            probe = command([clang, *compile_flags, '-O0', '-include', snapshot / config['header'],
                             '-MMD', '-MF', probe_depfile, '-MT', 'routine-object', '-c', snapshot / probe_name,
                             '-o', outdir / 'interface-probe.obj'], outdir, 'interface-probe', records, snapshot)
            require(probe.returncode == 0, 'Frozen header must declare routine_name at global scope; inspect interface-probe.stderr.txt')
            inspect_dependencies(probe_depfile, snapshot, report['snapshot_files'])
            for optimization in ('O0', 'O2'):
                build = outdir / optimization
                build.mkdir()
                objects = []
                outcome = {'status': 'failed', 'tests': 'not_provided' if not config['tests'] else 'not_run'}
                report['optimization_results'][optimization] = outcome
                for index, relative in enumerate([config['source'], *config['support_sources'], *config['tests']]):
                    obj = build / ('unit-' + str(index).zfill(3) + '.obj')
                    depfile = build / ('unit-' + str(index).zfill(3) + '.d')
                    label = optimization.lower() + '-compile-' + str(index).zfill(3)
                    forced_header = ['-include', snapshot / config['header']] if index == 0 else []
                    result = command([clang, *compile_flags, '-' + optimization, *forced_header,
                                      '-MMD', '-MF', depfile, '-MT', 'routine-object', '-c', snapshot / relative, '-o', obj], outdir, label, records, snapshot)
                    require(result.returncode == 0, label + ' failed; inspect compiler stderr')
                    inspect_dependencies(depfile, snapshot, report['snapshot_files'])
                    objects.append(obj)
                undefined = command([nm, '--undefined-only', objects[0]], outdir, optimization.lower() + '-undefined-symbols', records, snapshot)
                public = command([nm, '--defined-only', '--extern-only', objects[0]], outdir, optimization.lower() + '-public-symbols', records, snapshot)
                require(undefined.returncode == 0 and public.returncode == 0, 'Object symbol inspection failed')
                undefined_symbols = sorted(line.split()[-1] for line in undefined.stdout.splitlines() if line.strip())
                public_symbols = sorted(line.split()[-1] for line in public.stdout.splitlines() if line.strip())
                outcome['undefined_symbols'], outcome['public_symbols'] = undefined_symbols, public_symbols
                require(set(undefined_symbols) <= set(config['allowed_undefined_symbols']), 'Unexpected undefined symbols: ' + repr(undefined_symbols))
                require(config['routine_name'] in public_symbols and set(public_symbols) <= set(config['allowed_public_symbols']) | {config['routine_name']}, 'Unexpected/missing public symbols: ' + repr(public_symbols))
                outcome['object_sha256'] = digest(objects[0].read_bytes())
                if config['tests']:
                    executable = build / ('host-tests.exe' if os.name == 'nt' else 'host-tests')
                    linked = command([clang, *FLAGS, '-' + optimization, *objects, '-o', executable], outdir, optimization.lower() + '-link-tests', records, snapshot)
                    require(linked.returncode == 0, optimization + ' test link failed')
                    outcome['tests'], report['test_execution'] = 'incomplete', 'incomplete'
                    tested = command([executable], outdir, optimization.lower() + '-tests', records, snapshot)
                    outcome['test_returncode'], outcome['test_output'] = tested.returncode, tested.stdout
                    outcome['tests'] = 'passed' if tested.returncode == 0 else 'failed'
                    report['test_execution'] = 'incomplete' if tested.returncode == 0 else 'failed'
                    require(tested.returncode == 0, optimization + ' acceptance tests failed')
                    outcome['executable_sha256'] = digest(executable.read_bytes())
                outcome['status'] = 'passed'
            if config['tests']:
                report['test_execution'] = 'passed'
            for name, sha in report['files'].items():
                require(digest(safe_path(snapshot, name).read_bytes()) == sha, 'Verification snapshot changed during execution: ' + name)
                if name not in ('verifier-used.py', probe_name):
                    require(digest(safe_path(job, name).read_bytes()) == sha, 'Job changed during verification: ' + name)
            if config['tests']:
                report['test_execution'], report['status'] = 'passed', 'passed'
            else:
                report['status'] = 'compiled_only'
        except Exception as exc:
            report['error'] = str(exc)
        finally:
            save_new(outdir / 'verification.json', report)
    return {'status': report['status'], 'report': str(outdir / 'verification.json'), 'scope': report['scope'],
            'test_execution': report['test_execution'], **({'error': report['error']} if 'error' in report else {})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('doctor')
    create = commands.add_parser('prepare')
    create.add_argument('--spec', type=Path, required=True)
    create.add_argument('--verification-profile', type=Path)
    for command_parser in (create, commands.add_parser('record'), commands.add_parser('verify')):
        command_parser.add_argument('--workspace', type=Path, required=True)
        command_parser.add_argument('--job', required=True)
        if command_parser.prog.endswith(' record'):
            command_parser.add_argument('--generation', required=True)
            command_parser.add_argument('--agent', required=True)
            command_parser.add_argument('--agent-version', required=True)
            command_parser.add_argument('--bob-executed', choices=['yes', 'no'], required=True)
            command_parser.add_argument('--note', required=True)
        if command_parser.prog.endswith(' verify'):
            command_parser.add_argument('--clang', type=Path, required=True)
            command_parser.add_argument('--run', required=True)
    args = parser.parse_args()
    try:
        release, release_sha = doctor()
        result = {'status': 'ok', 'version': VERSION, 'release_sha256': release_sha} if args.command == 'doctor' else globals()[args.command](args, release, release_sha)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result['status'] == 'failed' else 0
    except Exception as exc:
        print(json.dumps({'status': 'error', 'message': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
