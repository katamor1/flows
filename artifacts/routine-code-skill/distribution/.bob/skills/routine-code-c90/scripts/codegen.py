"""Fixed case preparation/provenance wrapper; routine logic is written by the AI."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT.parents[1]
SAFE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z')
PROFILE = 'alarm-qualification-v01'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(content):
    return hashlib.sha256(content).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as output:
        output.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


@contextmanager
def owned_guard(path):
    handle = path.open('x')
    try:
        with handle:
            yield
    finally:
        path.unlink()


def safe_path(base, relative):
    base = base.resolve()
    path = base / relative
    require(not Path(relative).is_absolute() and path.resolve().is_relative_to(base), 'Path escapes job root')
    current = path
    while current != base:
        require(not current.is_symlink() and not current.is_junction(), 'Links/junctions are unsupported in jobs')
        current = current.parent
    return path


def doctor():
    release = load(ROOT / 'release.json')
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
    require(actual == set(release['files']) | {'release.json'}, 'Package inventory mismatch')
    for name, sha in release['files'].items():
        path = safe_path(ROOT, name)
        require(digest(path.read_bytes()) == sha, 'Package resource changed: ' + name)
    require(sys.version_info[:2] == (3, 12), 'This release is verified with Python 3.12')
    return release, digest((ROOT / 'release.json').read_bytes())


def job_path(args):
    require(SAFE_ID.fullmatch(args.job), 'Invalid job ID')
    workspace = args.workspace.expanduser().resolve()
    require(not workspace.is_relative_to(BUNDLE), 'Jobs must be outside the package')
    return workspace, safe_path(workspace, args.job)


def job_contract(sha):
    return {'format_version': '0.1.0', 'spec': 'input/spec.json', 'spec_sha256': sha,
            'header': 'include/AlarmQualification.h', 'source': 'src/AlarmQualification.c',
            'test': 'tests/test_alarm_qualification.c',
            'exported_object_symbol': 'AlarmQualification_Update'}


def checked_job(args, release, release_sha):
    _, job = job_path(args)
    lock = load(safe_path(job, 'package-lock.json'))
    require(lock['profile'] == PROFILE and lock['release_sha256'] == release_sha, 'Job package lock mismatch')
    expected_files = {name.removeprefix('assets/alarm-profile/'): sha
                      for name, sha in release['files'].items() if name.startswith('assets/alarm-profile/')}
    require(lock['files'] == expected_files, 'Job asset lock inventory mismatch')
    for name, sha in expected_files.items():
        require(digest(safe_path(job, name).read_bytes()) == sha, 'Fixed job asset changed: ' + name)
    config = load(safe_path(job, 'job.json'))
    require({k: v for k, v in config.items() if k != 'generation_record'} == job_contract(release['spec_sha256']), 'Job contract changed')
    require(re.fullmatch(r'records/[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.json', config['generation_record']) is not None,
            'Invalid generation record path')
    return job, config


def prepare(args, release, release_sha):
    content = args.spec.expanduser().resolve(strict=True).read_bytes()
    require(digest(content) == release['spec_sha256'],
            'No registered automatic verification profile for this specification. Use the generic skill workflow and approved project build/tests; do not change fixed assets.')
    workspace, job = job_path(args)
    workspace.mkdir(parents=True, exist_ok=True)
    guard = safe_path(workspace, '.' + args.job + '.lock')
    with owned_guard(guard):
        stage = None
        try:
            require(not job.exists(), 'Job already exists; choose a new job ID')
            stage = Path(tempfile.mkdtemp(prefix='.' + args.job + '-', dir=workspace)).resolve()
            asset_root = ROOT / 'assets/alarm-profile'
            files = {}
            for source in sorted(asset_root.rglob('*')):
                if source.is_file():
                    name = source.relative_to(asset_root).as_posix()
                    target = safe_path(stage, name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    files[name] = digest(target.read_bytes())
            for name in ('src', 'records'):
                (stage / name).mkdir()
            save_new(stage / 'job.json', {**job_contract(release['spec_sha256']), 'generation_record': 'records/pending.json'})
            save_new(stage / 'package-lock.json', {'format_version': '0.1.0', 'profile': PROFILE,
                                                 'release_sha256': release_sha, 'files': files})
            save_new(stage / 'input-origin.json', {'source_path': str(args.spec.resolve()),
                                                 'source_sha256': digest(content), 'canonical_copy': 'input/spec.json'})
            require(not job.exists(), 'Output appeared during preparation')
            stage.rename(job)
            stage = None
        finally:
            if stage is not None and stage.exists():
                require(stage.parent == workspace and stage.name.startswith('.' + args.job + '-'), 'Invalid cleanup path')
                shutil.rmtree(stage)
    return {'status': 'prepared', 'job': str(job), 'source_to_generate': str(job / 'src/AlarmQualification.c'),
            'header': str(job / 'include/AlarmQualification.h'), 'implementation_included': False}


def record(args, release, release_sha):
    job, config = checked_job(args, release, release_sha)
    require(SAFE_ID.fullmatch(args.generation), 'Invalid generation ID')
    require(args.agent.strip() and args.agent_version.strip() and args.note.strip(), 'Generation provenance must be explicit')
    require(args.bob_executed != 'yes' or 'bob' in args.agent.lower(), 'Bob execution declaration conflicts with agent name')
    source = safe_path(job, config['source'])
    source.read_text(encoding='ascii')
    mapping = safe_path(job, 'traceability.md')
    require(mapping.is_file() and mapping.stat().st_size > 0, 'Create traceability.md before recording this generation')
    path = safe_path(job, 'records/' + args.generation + '.json')
    value = {'format_version': '0.1.0', 'time_utc': datetime.now(timezone.utc).isoformat(),
             'agent': args.agent, 'agent_version': args.agent_version,
             'bob_executed': args.bob_executed == 'yes', 'status': 'draft_trial',
             'input_spec_sha256': digest(safe_path(job, config['spec']).read_bytes()),
             'header_sha256': digest(safe_path(job, config['header']).read_bytes()),
             'test_sha256': digest(safe_path(job, config['test']).read_bytes()),
             'source_sha256': digest(source.read_bytes()), 'traceability_sha256': digest(mapping.read_bytes()),
             'release_sha256': release_sha, 'note': args.note,
             'test_authorship': 'Reused independent specification-based PoC acceptance tests; not generated with this source.'}
    save_new(path, value)
    config['generation_record'] = path.relative_to(job).as_posix()
    pending = safe_path(job, '.job-update-' + args.generation + '.json')
    save_new(pending, config)
    os.replace(pending, job / 'job.json')
    return {'status': 'recorded', 'record': str(path), 'source_sha256': value['source_sha256']}


def verify(args, release, release_sha):
    job, config = checked_job(args, release, release_sha)
    require(SAFE_ID.fullmatch(args.run), 'Invalid run ID')
    generation = load(safe_path(job, config['generation_record']))
    require(generation['release_sha256'] == release_sha and generation['status'] == 'draft_trial', 'Generation identity mismatch')
    require(digest(safe_path(job, 'traceability.md').read_bytes()) == generation['traceability_sha256'], 'Traceability changed after recording')
    result = subprocess.run([sys.executable, '-X', 'utf8', '-S', '-B',
                             str(job / 'tools/codeflow.py'), 'verify', '--clang', str(args.clang),
                             '--output', 'qa/' + args.run], capture_output=True, text=True,
                            encoding='utf-8', errors='strict', timeout=180, shell=False)
    require(result.returncode == 0, 'Fixed verifier failed: ' + result.stderr + result.stdout)
    report = load(safe_path(job, 'qa/' + args.run + '/verification.json'))
    require(report['status'] == 'passed', 'Host verification did not pass')
    return {'status': 'passed', 'report': str(job / 'qa' / args.run / 'verification.json'),
            'scope': 'Windows host C90 O0/O2, specification-based acceptance tests; RTOS/ABI/WCET remain unverified'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('doctor')
    create = commands.add_parser('prepare')
    create.add_argument('--spec', type=Path, required=True)
    for command in (create, commands.add_parser('record'), commands.add_parser('verify')):
        command.add_argument('--workspace', type=Path, required=True)
        command.add_argument('--job', required=True)
        if command.prog.endswith(' record'):
            command.add_argument('--generation', required=True)
            command.add_argument('--agent', required=True)
            command.add_argument('--agent-version', required=True)
            command.add_argument('--bob-executed', choices=['yes', 'no'], required=True)
            command.add_argument('--note', required=True)
        if command.prog.endswith(' verify'):
            command.add_argument('--clang', type=Path, required=True)
            command.add_argument('--run', required=True)
    args = parser.parse_args()
    try:
        release, release_sha = doctor()
        result = {'status': 'ok', 'profile': PROFILE, 'release_sha256': release_sha} if args.command == 'doctor' else globals()[args.command](args, release, release_sha)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'error', 'message': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
