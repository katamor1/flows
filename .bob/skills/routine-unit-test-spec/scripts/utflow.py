"""Locked project inputs -> generic unit-test JSON -> OfficeCLI -> DOCX."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT.parents[1] if ROOT.parent.name == 'skills' else ROOT
SAFE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z')

def require(condition, message):
    if not condition: raise ValueError(message)
def digest(content): return hashlib.sha256(content).hexdigest()
def sha(path): return digest(path.read_bytes())
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def contained(base, relative):
    require(isinstance(relative, str) and bool(relative) and not Path(relative).is_absolute(), 'Expected a job-relative path')
    candidate = base/relative
    final = candidate.resolve()
    require(final.is_relative_to(base), 'Path escapes the allowed root')
    current = candidate
    while current != base:
        require(not current.is_symlink() and not current.is_junction(), 'Links and junctions are not supported inside jobs')
        current = current.parent
    return candidate

def doctor(exe):
    release = load(ROOT/'release.json')
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
    require(actual == set(release['files'])|{'release.json'}, 'Missing or unexpected package resources')
    for name, expected in release['files'].items():
        path = ROOT/name
        require(path.resolve().is_relative_to(ROOT) and not path.is_symlink(), 'Invalid package resource path')
        require(sha(path) == expected, 'Package hash mismatch: '+name)
    require(platform.python_version_tuple()[:2] == ('3', '12'), 'This release uses Python 3.12')
    require(exe.is_absolute() and exe.is_file() and exe.suffix.lower() == '.exe', 'Specify an existing absolute OfficeCLI .exe path')
    exe = exe.resolve()
    binary_hash = sha(exe)
    require(binary_hash == release['officecli']['sha256'], 'OfficeCLI binary is not approved for this release')
    proc = subprocess.run([str(exe), '--version'], capture_output=True, text=True, encoding='utf-8', timeout=15,
                          env={**os.environ, 'OFFICECLI_NO_AUTO_RESIDENT': '1'})
    require(proc.returncode == 0 and proc.stdout.strip() == release['officecli']['version'], 'Unsupported OfficeCLI version')
    return release, {'version': proc.stdout.strip(), 'sha256': binary_hash}, exe

def identity(release, renderer):
    return {'name': release['name'], 'version': release['version'], 'profile_id': release['profile_id'],
            'release_sha256': sha(ROOT/'release.json'), 'renderer': renderer}
def job_path(args):
    require(SAFE_ID.fullmatch(args.job), 'Invalid job ID')
    workspace = args.workspace.expanduser().resolve()
    require(not workspace.is_relative_to(BUNDLE), 'Jobs must be outside the package')
    return workspace, contained(workspace, args.job)
def publish_stage(stage, destination):
    for attempt in range(20):
        require(not destination.exists(), 'Output appeared during generation')
        try:
            stage.rename(destination)
            return
        except PermissionError as exc:
            if getattr(exc, 'winerror', None) not in (5, 32) or attempt == 19: raise
            time.sleep(0.1)
@contextmanager
def stage_directory(parent, name):
    parent.mkdir(parents=True, exist_ok=True)
    destination = contained(parent, name)
    lock = contained(parent, '.'+name+'.lock')
    owned = lock.open('x', encoding='utf-8')
    try:
        with owned:
            stage = None
            try:
                require(not destination.exists(), 'ID already exists; choose a new ID')
                stage = Path(tempfile.mkdtemp(prefix='.'+name+'-', dir=parent)).resolve()
                yield stage, destination
                require(not destination.exists(), 'Output appeared during generation')
                publish_stage(stage, destination)
            finally:
                if stage is not None and stage.exists():
                    require(stage.parent == parent.resolve() and stage.name.startswith('.'+name+'-'), 'Invalid staging cleanup path')
                    shutil.rmtree(stage)
    finally: lock.unlink()

def check_generation_record(record, contents, bindings, file_map):
    for key, role in (('input_spec_sha256', 'spec'), ('source_sha256', 'source'), ('header_sha256', 'header')):
        require(record.get(key) == digest(contents[bindings[role]]), 'Code generation record mismatch: '+key)
    hashes = record.get('file_hashes', {})
    require(type(hashes) is dict and set(hashes) == set(file_map), 'Generation asset inventory mismatch')
    for origin, expected in hashes.items():
        require(digest(contents[file_map[origin]]) == expected, 'Generation asset hash mismatch: '+origin)

def read_code_job(path):
    code_job = path.expanduser().resolve()
    require(code_job.is_dir(), 'Code job directory does not exist')
    config = load(contained(code_job, 'job.json'))
    require(config.get('format_version') in ('0.1.0', '0.2.0'), 'Unsupported code job version')
    origins = {role: config[role] for role in ('spec', 'source', 'header', 'generation_record')}
    source_paths = {role: contained(code_job, origin) for role, origin in origins.items()}
    contents, bindings = {}, {}
    for role, path in source_paths.items():
        name = 'inputs/program-spec.json' if role == 'spec' else 'inputs/generation-record.json' if role == 'generation_record' else 'inputs/'+role+'/'+path.name
        contents[name] = path.read_bytes()
        bindings[role] = name
    record = json.loads(contents[bindings['generation_record']].decode('utf-8'))
    file_map = {}
    for origin in record.get('file_hashes', {}):
        path = contained(code_job, origin)
        roles = [role for role, original in origins.items() if original == origin]
        if roles: name = bindings[roles[0]]
        else:
            name = 'inputs/assets/'+Path(origin).as_posix()
            contents[name] = path.read_bytes()
        file_map[origin] = name
    check_generation_record(record, contents, bindings, file_map)
    if 'spec_sha256' in config: require(config['spec_sha256'] == digest(contents[bindings['spec']]), 'Code job specification hash mismatch')
    return contents, {'format_version': '0.2.0', 'copied_from': str(code_job), 'provenance': 'generation_record',
                      'bindings': bindings, 'generation_file_map': file_map,
                      'files': {name: digest(content) for name, content in contents.items()}}

def read_external(args):
    require(all((args.program_spec, args.source, args.header)), 'Supply --code-job or all of --program-spec --source --header')
    contents, bindings = {}, {}
    for role, raw in (('spec', args.program_spec), ('source', args.source), ('header', args.header)):
        path = raw.expanduser().resolve()
        name = 'inputs/program-spec.json' if role == 'spec' else 'inputs/'+role+'/'+path.name
        contents[name] = path.read_bytes()
        bindings[role] = name
    return contents, {'format_version': '0.2.0', 'copied_from': 'explicit_project_inputs',
                      'origins': {role: str(path.expanduser().resolve()) for role, path in (('spec', args.program_spec), ('source', args.source), ('header', args.header))},
                      'provenance': 'external/not_provided', 'bindings': bindings, 'generation_file_map': {},
                      'files': {name: digest(content) for name, content in contents.items()}}

def target_hashes(lock):
    return {key: lock['files'][lock['bindings'][role]] for key, role in
            (('program_spec_sha256', 'spec'), ('source_sha256', 'source'), ('header_sha256', 'header'))}

def read_inputs(job):
    lock_path = contained(job, 'input-lock.json')
    lock_bytes = lock_path.read_bytes()
    lock = json.loads(lock_bytes.decode('utf-8'))
    require(lock.get('format_version') == '0.2.0', 'Unsupported input lock')
    require(set(lock['bindings']) in ({'spec', 'source', 'header'}, {'spec', 'source', 'header', 'generation_record'}), 'Input bindings mismatch')
    contents = {name: contained(job, name).read_bytes() for name in lock['files']}
    for name, expected in lock['files'].items(): require(digest(contents[name]) == expected, 'Locked input hash mismatch: '+name)
    require(set(lock['bindings'].values()) <= set(contents), 'Input lock inventory mismatch')
    if lock['provenance'] == 'generation_record':
        record = json.loads(contents[lock['bindings']['generation_record']].decode('utf-8'))
        check_generation_record(record, contents, lock['bindings'], lock['generation_file_map'])
    else: require(lock['provenance'] == 'external/not_provided' and 'generation_record' not in lock['bindings'], 'Invalid external provenance')
    require(lock_path.read_bytes() == lock_bytes, 'Input lock changed while reading inputs')
    return json.loads(contents[lock['bindings']['spec']].decode('utf-8')), lock, lock_bytes

def validated_source(content, release, program_spec, target):
    import _contract
    import _renderer
    data = _contract.validate(json.loads(content.decode('utf-8')), load(ROOT/release['schema']), program_spec, target)
    require(data['document']['template_id'] == release['template_id'], 'Unsupported template ID')
    _renderer.check_xml_characters(data)
    return data

def skeleton(program, target, args):
    doc = program['document']
    return {'schema_version': '0.2.0', 'document': {'id': args.document_id or 'UTS-'+args.job,
            'title': doc['routine_name']+' 単体テスト仕様書', 'revision': '0.1', 'date': date.today().isoformat(),
            'status': doc.get('status', 'draft'), 'status_label': doc.get('status_label', doc.get('status', 'draft')),
            'routine_id': doc['routine_id'], 'routine_name': doc['routine_name'], 'template_id': 'unit-test-spec-v02',
            'author': '未記入'}, 'target': target, 'summary': '', 'environment': [],
            'assumptions': program.get('trial_assumptions', []), 'cases': [], 'families': [], 'static_checks': [],
            'coverage': [], 'open_issues': program.get('open_issues', [])}

def execute(args):
    release, renderer, exe = doctor(args.officecli)
    package = identity(release, renderer)
    if args.command == 'doctor': return {'status': 'ok', 'package': package, 'renderer': renderer, 'python': platform.python_version(), 'third_party_python_dependencies': []}
    if args.command == 'describe': return {**package, 'schema': str(ROOT/release['schema']), 'example': str(ROOT/release['example']),
                'template_id': release['template_id'], 'template_revision': release['template_revision'], 'limits': release['limits']}
    workspace, job = job_path(args)
    import _contract
    if args.command == 'new-job':
        require(not args.code_job or not any((args.program_spec, args.source, args.header)), 'Choose --code-job or explicit project inputs')
        inputs, lock = read_code_job(args.code_job) if args.code_job else read_external(args)
        with stage_directory(workspace, args.job) as (stage, _):
            for folder in ('inputs', 'source', 'records'): (stage/folder).mkdir()
            for name, content in inputs.items():
                destination = contained(stage, name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
            save(stage/'input-lock.json', lock)
            program_spec, _, lock_bytes = read_inputs(stage)
            save(stage/'package-lock.json', {'package': package, 'input_lock_sha256': digest(lock_bytes)})
            if args.unit_test_spec:
                source_bytes = args.unit_test_spec.expanduser().resolve().read_bytes()
                data = validated_source(source_bytes, release, program_spec, target_hashes(lock))
                (stage/'source/unit-test-spec.json').write_bytes(source_bytes)
            else:
                data = skeleton(program_spec, target_hashes(lock), args)
                save(stage/'source/unit-test-spec.json', data)
            record = _contract.execution_record(data)
            _contract.validate_execution(record, data)
            save(stage/'records/execution-record.json', record)
            (stage/'.gitattributes').write_bytes(b'* -text\n')
        return {'status': 'created', 'authoring_required': not bool(args.unit_test_spec), 'source': str(job/'source/unit-test-spec.json'), 'execution_record': str(job/'records/execution-record.json')}
    program_spec, input_lock, input_lock_bytes = read_inputs(job)
    expected_lock = {'package': package, 'input_lock_sha256': digest(input_lock_bytes)}
    require(load(contained(job, 'package-lock.json')) == expected_lock, 'Job release, renderer, or input lock mismatch')
    source = contained(job, 'source/unit-test-spec.json')
    content = source.read_bytes()
    data = validated_source(content, release, program_spec, target_hashes(input_lock))
    execution_bytes = contained(job, 'records/execution-record.json').read_bytes()
    _contract.validate_execution(json.loads(execution_bytes.decode('utf-8')), data)
    if args.command == 'validate': return {'status': 'valid', 'source_sha256': digest(content), 'input_lock_sha256': digest(input_lock_bytes), 'execution_record_sha256': digest(execution_bytes), 'document_status': data['document']['status']}
    require(SAFE_ID.fullmatch(args.run), 'Invalid render ID')
    import _renderer
    with stage_directory(contained(job, 'renders'), args.run) as (stage, destination):
        snapshot = stage/'unit-test-spec.json'
        snapshot.write_bytes(content)
        (stage/'input-lock.json').write_bytes(input_lock_bytes)
        (stage/'execution-record.json').write_bytes(execution_bytes)
        save(stage/'traceability.json', _contract.traceability(data))
        output = stage/'unit-test-spec.docx'
        record = _renderer.build(snapshot, ROOT/release['schema'], ROOT/release['template'], output, stage/'manifest.json', exe, data)
        _, current_lock, current_bytes = read_inputs(job)
        require(current_lock == input_lock and current_bytes == input_lock_bytes, 'Input lock changed during rendering')
        require(source.read_bytes() == content and contained(job, 'records/execution-record.json').read_bytes() == execution_bytes, 'Canonical source or execution record changed during rendering')
        require(load(contained(job, 'package-lock.json')) == expected_lock, 'Package lock changed during rendering')
        record.update({'package': package, 'officecli': renderer, 'python': platform.python_version(), 'canonical_source': 'source/unit-test-spec.json',
                       'input_files': input_lock['files'], 'input_provenance': input_lock['provenance'], 'input_lock_sha256': digest(input_lock_bytes),
                       'execution_record_sha256': digest(execution_bytes), 'traceability_sha256': sha(stage/'traceability.json'),
                       'schema': release['schema'], 'template': release['template'], 'template_id': release['template_id'], 'template_revision': release['template_revision']})
        save(stage/'manifest.json', record)
    return {'status': 'rendered', 'document': str(destination/output.name), 'manifest': str(destination/'manifest.json'),
            'document_status': data['document']['status'], 'test_execution': 'not_executed'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('doctor', 'describe', 'new-job', 'validate', 'render'):
        command = commands.add_parser(name)
        command.add_argument('--officecli', required=True, type=Path)
        if name in ('new-job', 'validate', 'render'):
            command.add_argument('--workspace', required=True, type=Path)
            command.add_argument('--job', required=True)
        if name == 'new-job':
            for flag in ('code-job', 'program-spec', 'source', 'header', 'unit-test-spec'): command.add_argument('--'+flag, type=Path)
            command.add_argument('--document-id')
        if name == 'render': command.add_argument('--run', required=True)
    args = parser.parse_args()
    try: print(json.dumps(execute(args), ensure_ascii=False, indent=2))
    except Exception as exc:
        print(json.dumps({'status': 'error', 'message': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0
if __name__ == '__main__': sys.exit(main())
