"""Fixed frozen program/C90 inputs -> unit-test JSON -> OfficeCLI -> DOCX workflow."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
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
FROZEN_INPUTS = {
    'inputs/program-spec.json': '097b1185e284c17805b51c92dd821d1bec64f55d0ce1781c2c1fb369239b4265',
    'inputs/AlarmQualification.c': 'e2b910d6aaf0932a19c3f287cb6513a5193a9e365435c5876a29cd7684683bee',
    'inputs/AlarmQualification.h': '3f8799a676201b23a2fa96e7eddfaf4fe99a67429edb2e460571197a238bcf00',
}
INPUT_ORIGINS = {
    'inputs/program-spec.json': 'input/spec.json',
    'inputs/AlarmQualification.c': 'src/AlarmQualification.c',
    'inputs/AlarmQualification.h': 'include/AlarmQualification.h',
    'inputs/generation-record.json': 'generation-record.json',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(content):
    return hashlib.sha256(content).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def contained(base, relative):
    candidate = base/relative
    final = candidate.resolve()
    require(final.is_relative_to(base), 'Path escapes the allowed root')
    require(not final.is_relative_to(BUNDLE), 'Jobs must be outside the package')
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
    require(release['input_files'] == FROZEN_INPUTS, 'Release frozen input profile mismatch')
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
            if getattr(exc, 'winerror', None) not in (5, 32) or attempt == 19:
                raise
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
    finally:
        lock.unlink()


def check_generation_record(content):
    record = json.loads(content.decode('utf-8'))
    for key, filename in (('input_spec_sha256', 'inputs/program-spec.json'),
                          ('source_sha256', 'inputs/AlarmQualification.c'),
                          ('header_sha256', 'inputs/AlarmQualification.h')):
        require(record.get(key) == FROZEN_INPUTS[filename], 'Code generation record mismatch: '+key)
    require(record.get('status') == 'draft_trial', 'Code generation record is not the frozen draft trial')
    return record


def read_code_job(path):
    code_job = path.expanduser().resolve()
    require(code_job.is_dir(), 'Code job directory does not exist')
    require(not code_job.is_relative_to(BUNDLE), 'Code job must be outside the package')
    contents = {name: contained(code_job, origin).read_bytes() for name, origin in INPUT_ORIGINS.items()}
    for name, expected in FROZEN_INPUTS.items():
        require(digest(contents[name]) == expected, 'Code job input hash mismatch: '+name)
    check_generation_record(contents['inputs/generation-record.json'])
    return code_job, contents


def read_inputs(job):
    lock_path = contained(job, 'input-lock.json')
    lock_bytes = lock_path.read_bytes()
    lock = json.loads(lock_bytes.decode('utf-8'))
    require(lock.get('format_version') == '0.1.0' and lock.get('routine_id') == 'RTN-ALM-001', 'Unsupported input lock')
    files = lock.get('files', {})
    require(set(files) == set(INPUT_ORIGINS), 'Input lock inventory mismatch')
    for name, expected in FROZEN_INPUTS.items():
        require(files[name] == expected, 'Frozen input lock mismatch: '+name)
    contents = {name: contained(job, name).read_bytes() for name in files}
    for name, expected in files.items():
        require(digest(contents[name]) == expected, 'Frozen input hash mismatch: '+name)
    check_generation_record(contents['inputs/generation-record.json'])
    require(lock_path.read_bytes() == lock_bytes, 'Input lock changed while reading inputs')
    return json.loads(contents['inputs/program-spec.json'].decode('utf-8')), lock, lock_bytes


def validated_source(content, release, program_spec):
    import _contract
    import _renderer
    data = _contract.validate(json.loads(content.decode('utf-8')), load(ROOT/release['schema']), program_spec)
    require(data['target'] == release['target'], 'Source target hashes differ from the release profile')
    require(data['document']['routine_id'] == release['routine_id'], 'Unsupported routine for this profile')
    require(data['document']['template_id'] == release['template_id'], 'Unsupported template ID')
    require(data['document']['status_label'] == '試作仕様 要件確認前', 'This release cannot create approved specifications')
    require(SAFE_ID.fullmatch(data['document']['id']), 'Invalid document ID')
    _renderer.check_xml_characters(data)
    return data


def execute(args):
    release, renderer, exe = doctor(args.officecli)
    package = identity(release, renderer)
    if args.command == 'doctor':
        return {'status': 'ok', 'package': package, 'renderer': renderer,
                'python': platform.python_version(), 'third_party_python_dependencies': []}
    if args.command == 'describe':
        return {**package, 'schema': str(ROOT/release['schema']), 'example': str(ROOT/release['example']),
                'template_id': release['template_id'], 'template_revision': release['template_revision'],
                'input_files': FROZEN_INPUTS, 'limits': release['limits']}
    workspace, job = job_path(args)
    import _contract
    if args.command == 'new-job':
        code_job, inputs = read_code_job(args.code_job)
        with stage_directory(workspace, args.job) as (stage, _):
            (stage/'inputs').mkdir()
            (stage/'source').mkdir()
            (stage/'records').mkdir()
            for name, content in inputs.items():
                (stage/name).write_bytes(content)
            save(stage/'input-lock.json', {'format_version': '0.1.0', 'routine_id': release['routine_id'],
                                          'copied_from': str(code_job),
                                          'files': {name: digest(content) for name, content in inputs.items()}})
            save(stage/'package-lock.json', package)
            source_bytes = (ROOT/release['example']).read_bytes()
            program_spec, _, _ = read_inputs(stage)
            data = validated_source(source_bytes, release, program_spec)
            (stage/'source/unit-test-spec.json').write_bytes(source_bytes)
            record = _contract.execution_record(data)
            _contract.validate_execution(record, data)
            save(stage/'records/execution-record.json', record)
        return {'status': 'created', 'source': str(job/'source/unit-test-spec.json'),
                'execution_record': str(job/'records/execution-record.json')}
    require(load(contained(job, 'package-lock.json')) == package, 'Job release or renderer lock mismatch')
    program_spec, input_lock, input_lock_bytes = read_inputs(job)
    source = contained(job, 'source/unit-test-spec.json')
    content = source.read_bytes()
    data = validated_source(content, release, program_spec)
    execution_bytes = contained(job, 'records/execution-record.json').read_bytes()
    _contract.validate_execution(json.loads(execution_bytes.decode('utf-8')), data)
    if args.command == 'validate':
        return {'status': 'valid', 'source_sha256': digest(content), 'input_lock_sha256': digest(input_lock_bytes),
                'execution_record_sha256': digest(execution_bytes), 'document_status': data['document']['status']}
    require(SAFE_ID.fullmatch(args.run), 'Invalid render ID')
    import _renderer
    with stage_directory(contained(job, 'renders'), args.run) as (stage, destination):
        snapshot = stage/'unit-test-spec.json'
        snapshot.write_bytes(content)
        (stage/'input-lock.json').write_bytes(input_lock_bytes)
        (stage/'execution-record.json').write_bytes(execution_bytes)
        save(stage/'traceability.json', _contract.traceability(data))
        output = stage/(data['document']['id']+'.docx')
        record = _renderer.build(snapshot, ROOT/release['schema'], ROOT/release['template'],
                                 output, stage/'manifest.json', exe, data)
        # Detect changes to the frozen lock or bytes during an OfficeCLI operation.
        _, current_lock, current_lock_bytes = read_inputs(job)
        require(current_lock == input_lock and current_lock_bytes == input_lock_bytes, 'Input lock changed during rendering')
        require(load(contained(job, 'package-lock.json')) == package, 'Package lock changed during rendering')
        record.update({'package': package, 'officecli': renderer, 'python': platform.python_version(),
                       'canonical_source': 'source/unit-test-spec.json', 'input_files': input_lock['files'],
                       'input_lock_sha256': digest(input_lock_bytes),
                       'execution_record_sha256': digest(execution_bytes),
                       'traceability_sha256': sha(stage/'traceability.json'),
                       'schema': release['schema'], 'template': release['template'],
                       'template_id': release['template_id'], 'template_revision': release['template_revision']})
        save(stage/'manifest.json', record)
    return {'status': 'rendered', 'document': str(destination/output.name),
            'manifest': str(destination/'manifest.json'), 'document_status': 'draft_trial',
            'test_execution': 'not_executed'}


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
            command.add_argument('--code-job', required=True, type=Path)
        if name == 'render':
            command.add_argument('--run', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(execute(args), ensure_ascii=False, indent=2))
    except Exception as exc:
        print(json.dumps({'status': 'error', 'message': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
