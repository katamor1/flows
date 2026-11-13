"""Fixed-resource consumer CLI. Deliberately has no initialization commands."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT.parents[1] if ROOT.parent.name == 'skills' else ROOT
SAFE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def contained(base, relative):
    """Reject traversals and existing links, including Windows junctions."""
    path = base / relative
    resolved = path.resolve()
    require(resolved.is_relative_to(base), 'Path escapes its allowed root')
    require(not resolved.is_relative_to(BUNDLE), 'Jobs must be outside the package')
    current = path
    while current != base:
        require(not current.is_symlink() and not current.is_junction(),
                'Links and junctions are not supported inside a job workspace')
        current = current.parent
    return path


def doctor():
    release_path = ROOT / 'release.json'
    release = read_json(release_path)
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
    require(actual == set(release['files']) | {'release.json'},
            'Package files are missing or unexpected; reinstall this release')
    for name, expected in release['files'].items():
        path = ROOT / name
        require(path.resolve().is_relative_to(ROOT) and not path.is_symlink(),
                'Package asset points outside the release')
        require(digest(path) == expected, f'Package hash mismatch: {name}; reinstall this release')
    require(platform.python_version_tuple()[:2] == tuple(release['runtime']['python_minor'].split('.')),
            'Unsupported Python minor version; use the release runtime')
    for name, expected in release['runtime']['dependencies'].items():
        require(version(name) == expected, f'Dependency mismatch: {name}; use the release runtime')
    return release


def identity(release):
    return {'name': release['name'], 'version': release['version'],
            'profile_id': release['profile_id'], 'release_sha256': digest(ROOT / 'release.json')}


def job_path(args):
    require(SAFE_ID.fullmatch(args.job), 'Invalid job ID')
    workspace = args.workspace.expanduser().resolve()
    require(not workspace.is_relative_to(BUNDLE), 'Jobs must be outside the package')
    return workspace, contained(workspace, args.job)


@contextmanager
def stage_directory(parent, name):
    """Cooperating invocations serialize by ID; publish only complete directories."""
    parent.mkdir(parents=True, exist_ok=True)
    target = contained(parent, name)
    lock = contained(parent, '.' + name + '.lock')
    owned_lock = lock.open('x', encoding='utf-8')
    try:
        with owned_lock:
            stage = None
            try:
                require(not target.exists(), 'ID already exists; choose a new ID')
                stage = Path(tempfile.mkdtemp(prefix='.' + name + '-', dir=parent)).resolve()
                yield stage, target
                require(not target.exists(), 'Output appeared during generation; choose a new ID')
                stage.rename(target)
            finally:
                if stage is not None and stage.exists():
                    require(stage.parent == parent.resolve() and stage.name.startswith('.' + name + '-'),
                            'Refusing cleanup outside the staging directory')
                    shutil.rmtree(stage)
    finally:
        lock.unlink()


def load_job(args, release):
    _, job = job_path(args)
    lock = read_json(contained(job, 'package-lock.json'))
    require(lock == identity(release), 'Job release lock mismatch; use the pinned release')
    source = contained(job, 'source/spec.json')
    import _engine
    data = _engine.validate(read_json(source), read_json(ROOT / release['schema']))
    require(data['document']['routine_id'] == release['routine_id'], 'Unsupported routine for this profile')
    require(SAFE_ID.fullmatch(data['document']['id']), 'Invalid document ID')
    return job, source, data


def execute(args):
    release = doctor()
    package = identity(release)
    if args.command == 'doctor':
        return {'status': 'ok', 'package': package, 'runtime': runtime_info(release)}
    if args.command == 'describe':
        return {**package, 'schema': str(ROOT / release['schema']),
                'example': str(ROOT / release['example']), 'template_id': release['template_id'],
                'limits': release['limits']}
    if args.command == 'new-job':
        workspace, job = job_path(args)
        with stage_directory(workspace, args.job) as (stage, _):
            (stage / 'source').mkdir()
            shutil.copyfile(ROOT / release['example'], stage / 'source/spec.json')
            write_json(stage / 'package-lock.json', package)
        return {'status': 'created', 'job': str(job), 'source': str(job / 'source/spec.json')}
    job, source, data = load_job(args, release)
    if args.command == 'validate':
        return {'status': 'valid', 'source_sha256': digest(source),
                'document_status': data['document']['status'], 'package': package}
    require(SAFE_ID.fullmatch(args.run), 'Invalid render ID')
    renders = contained(job, 'renders')
    # Snapshot before generation; the manifest describes exactly these input bytes.
    content = source.read_bytes()
    import _engine
    snapshot_data = _engine.validate(json.loads(content.decode('utf-8')), read_json(ROOT / release['schema']))
    require(snapshot_data['document']['routine_id'] == release['routine_id'], 'Unsupported routine for this profile')
    doc_id = snapshot_data['document']['id']
    require(SAFE_ID.fullmatch(doc_id), 'Invalid document ID')
    with stage_directory(renders, args.run) as (stage, destination):
        snapshot = stage / 'spec.json'
        snapshot.write_bytes(content)
        document = stage / (doc_id + '.docx')
        manifest = stage / 'manifest.json'
        record = _engine.build(snapshot, ROOT / release['schema'], ROOT / release['template'], document, manifest)
        record.update({'package': package, 'runtime': runtime_info(release),
                       'source': 'spec.json', 'canonical_source': 'source/spec.json',
                       'visual_review': 'not_performed_by_this_command'})
        write_json(manifest, record)
    return {'status': 'rendered', 'document': str(destination / document.name),
            'manifest': str(destination / 'manifest.json'), 'document_status': 'draft_trial'}


def runtime_info(release):
    return {'python': platform.python_version(), 'platform': platform.platform(),
            'dependencies': {name: version(name) for name in release['runtime']['dependencies']}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('doctor', 'describe', 'new-job', 'validate', 'render'):
        cmd = commands.add_parser(command)
        if command in ('new-job', 'validate', 'render'):
            cmd.add_argument('--workspace', type=Path, required=True)
            cmd.add_argument('--job', required=True)
        if command == 'render':
            cmd.add_argument('--run', required=True)
    args = parser.parse_args()
    try:
        result = execute(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(json.dumps({'status': 'error', 'message': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
