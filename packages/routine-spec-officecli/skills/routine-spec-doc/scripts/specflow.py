"""Fixed JSON -> OfficeCLI -> DOCX workflow; Python standard library only."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
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
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    require(platform.python_version_tuple()[:2] == ('3', '12'), 'This release uses Python 3.12')
    require(exe.is_absolute() and exe.is_file() and exe.suffix.lower() == '.exe', 'Specify an existing absolute OfficeCLI .exe path')
    exe = exe.resolve()
    digest = sha(exe)
    require(digest == release['officecli']['sha256'], 'OfficeCLI binary is not approved for this release')
    proc = subprocess.run([str(exe), '--version'], capture_output=True, text=True, encoding='utf-8', timeout=15)
    require(proc.returncode == 0 and proc.stdout.strip() == release['officecli']['version'], 'Unsupported OfficeCLI version')
    renderer = {'version': proc.stdout.strip(), 'sha256': digest}
    return release, renderer, exe


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
            # Windows sync/indexing can briefly deny a newly created directory rename.
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


def validated_source(content, release):
    import _contract
    import _renderer
    data = _contract.validate(json.loads(content.decode('utf-8')), load(ROOT/release['schema']))
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
                'limits': release['limits']}
    workspace, job = job_path(args)
    if args.command == 'new-job':
        with stage_directory(workspace, args.job) as (stage, _):
            (stage/'source').mkdir()
            shutil.copyfile(ROOT/release['example'], stage/'source/spec.json')
            save(stage/'package-lock.json', package)
        return {'status': 'created', 'source': str(job/'source/spec.json')}
    require(load(contained(job, 'package-lock.json')) == package, 'Job release or renderer lock mismatch')
    source = contained(job, 'source/spec.json')
    content = source.read_bytes()
    data = validated_source(content, release)
    if args.command == 'validate':
        return {'status': 'valid', 'source_sha256': sha(source), 'document_status': data['document']['status']}
    require(SAFE_ID.fullmatch(args.run), 'Invalid render ID')
    import _renderer
    with stage_directory(contained(job, 'renders'), args.run) as (stage, destination):
        snapshot = stage/'spec.json'
        snapshot.write_bytes(content)
        output = stage/(data['document']['id']+'.docx')
        record = _renderer.build(snapshot, ROOT/release['schema'], ROOT/release['template'],
                                 output, stage/'manifest.json', exe, data)
        record.update({'package': package, 'officecli': renderer,
                       'python': platform.python_version(), 'canonical_source': 'source/spec.json'})
        save(stage/'manifest.json', record)
    return {'status': 'rendered', 'document': str(destination/output.name),
            'manifest': str(destination/'manifest.json'), 'document_status': 'draft_trial'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('doctor', 'describe', 'new-job', 'validate', 'render'):
        command = commands.add_parser(name)
        command.add_argument('--officecli', required=True, type=Path)
        if name in ('new-job', 'validate', 'render'):
            command.add_argument('--workspace', required=True, type=Path)
            command.add_argument('--job', required=True)
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
