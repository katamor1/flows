"""Build, verify and reversibly install the three fixed IBM Bob skills (stdlib only)."""
import argparse
import hashlib
import io
import json
import time
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0'
KITS = (
    ('routine-spec-officecli', '0.3.0', 'routine-spec-doc'),
    ('routine-code-c90', '0.2.0', 'routine-code-c90'),
    ('routine-unit-test-officecli', '0.2.0', 'routine-unit-test-spec'),
)
MANAGED = (
    '.bob/skills/routine-spec-doc', '.bob/skills/routine-code-c90',
    '.bob/skills/routine-unit-test-spec', '.bob/rules/20-routine-spec.md',
    '.bob/rules/30-routine-unit-test-spec.md', '.bob/rules/.gitattributes',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def read_zip(path):
    return read_zip_bytes(Path(path).read_bytes())


def read_zip_bytes(data):
    with ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP entries')
        for name in names:
            parts = PurePosixPath(name)
            if (not name or '\\' in name or parts.is_absolute() or
                    any(part in {'.', '..'} or ':' in part for part in parts.parts) or
                    parts.as_posix() != name or name.endswith('/')):
                raise ValueError('Unsafe ZIP entry: ' + name)
            mode = archive.getinfo(name).external_attr >> 16
            if mode & 0o170000 == 0o120000:
                raise ValueError('Symlink ZIP entry')
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC failure')
        return {name: archive.read(name) for name in names}


def verify_inventory(payload, manifest_name):
    manifest = json.loads(payload[manifest_name])
    files = manifest['files']
    if set(files) != set(payload) - {manifest_name}:
        raise ValueError('Distribution inventory mismatch')
    for name, expected in files.items():
        if sha(payload[name]) != expected:
            raise ValueError('Distribution hash mismatch: ' + name)
    return manifest


def verify_skill(payload, skill, expected_release):
    prefix = '.bob/skills/' + skill + '/'
    release_bytes = payload[prefix + 'release.json']
    if sha(release_bytes) != expected_release:
        raise ValueError('Release hash mismatch: ' + skill)
    release = json.loads(release_bytes)
    actual = {name[len(prefix):] for name in payload if name.startswith(prefix)}
    if actual != set(release['files']) | {'release.json'}:
        raise ValueError('Skill inventory mismatch: ' + skill)
    for name, expected in release['files'].items():
        if sha(payload[prefix + name]) != expected:
            raise ValueError('Unsealed skill resource: ' + name)
    if payload[prefix + '.gitattributes'] not in (b'* -text\n', b'* -text\r\n'):
        raise ValueError('Missing byte-preservation guard')
    return release


def build():
    payload = {}
    sources = []
    for name, version, skill in KITS:
        kit = ROOT.parent / name / 'dist'
        receipt = json.loads((kit / ('checksums-' + version + '.json')).read_bytes())
        filename = receipt.get('file', receipt.get('archive'))
        archive = kit / filename
        archive_bytes = archive.read_bytes()
        if sha(archive_bytes) != receipt['sha256']:
            raise ValueError('Source archive hash mismatch: ' + name)
        source = read_zip_bytes(archive_bytes)
        metadata = verify_inventory(source, 'distribution.json')
        release = verify_skill(source, skill, metadata['release_sha256'])
        if metadata['version'] != version or release['version'] != version:
            raise ValueError('Unexpected kit version: ' + name)
        for path, data in source.items():
            if path.startswith('.bob/'):
                if path in payload:
                    raise ValueError('Conflicting managed path: ' + path)
                payload[path] = data
        payload['guides/' + name + '.md'] = source['BOB-TEAM-README.md']
        payload['manifests/' + name + '.json'] = source['distribution.json']
        sources.append({'name': name, 'skill': skill, 'version': version,
                        'archive': filename, 'archive_sha256': receipt['sha256'],
                        'release_sha256': metadata['release_sha256']})
    payload['.bob/rules/.gitattributes'] = b'* -text\n'
    payload['README.md'] = (ROOT / 'README.md').read_bytes()
    payload['tools/manage.py'] = Path(__file__).read_bytes()
    payload['distribution.json'] = encoded({
        'name': 'ibm-bob-routine-development', 'version': VERSION,
        'sources': sources, 'managed_paths': list(MANAGED),
        'bob_chat_skill_activation': 'not_tested',
        'files': {name: sha(data) for name, data in sorted(payload.items())}})
    target = ROOT / 'dist' / ('ibm-bob-routine-development-' + VERSION + '.zip')
    target.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(target, 'w', compression=ZIP_DEFLATED) as archive:
        for name, data in sorted(payload.items()):
            info = ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    result = verify(target)
    result['archive'] = target.name
    (target.parent / ('checksums-' + VERSION + '.json')).write_bytes(encoded(result))
    return result


def verify(archive):
    archive_bytes = Path(archive).read_bytes()
    return verify_payload(read_zip_bytes(archive_bytes), archive_bytes)


def verify_payload(payload, archive_bytes):
    metadata = verify_inventory(payload, 'distribution.json')
    if metadata['name'] != 'ibm-bob-routine-development' or metadata['version'] != VERSION:
        raise ValueError('Wrong combined distribution')
    expected = {(name, version, skill) for name, version, skill in KITS}
    actual = {(s['name'], s['version'], s['skill']) for s in metadata['sources']}
    if actual != expected or len(metadata['sources']) != len(KITS):
        raise ValueError('Unexpected source kits')
    if metadata['managed_paths'] != list(MANAGED):
        raise ValueError('Unexpected install targets')
    for source in metadata['sources']:
        release = verify_skill(payload, source['skill'], source['release_sha256'])
        if release['version'] != source['version']:
            raise ValueError('Skill version differs from combined metadata')
        original = json.loads(payload['manifests/' + source['name'] + '.json'])
        if original['release_sha256'] != source['release_sha256']:
            raise ValueError('Source manifest differs')
        for name, expected_hash in original['files'].items():
            mapped = 'guides/' + source['name'] + '.md' if name == 'BOB-TEAM-README.md' else name
            if mapped not in payload or sha(payload[mapped]) != expected_hash:
                raise ValueError('Original kit payload differs: ' + name)
    bob_files = {name for name in payload if name.startswith('.bob/')}
    covered = {name for name in bob_files if any(name == p or name.startswith(p + '/') for p in MANAGED)}
    if covered != bob_files or payload['.bob/rules/.gitattributes'] != b'* -text\n':
        raise ValueError('Unmanaged Bob payload')
    return {'status': 'passed', 'version': VERSION,
            'sha256': sha(archive_bytes), 'size_bytes': len(archive_bytes),
            'entry_count': len(payload), 'skills': [s['skill'] for s in metadata['sources']]}


def checked_path(root, relative):
    target = root / relative
    if target.resolve() != target.absolute() or not target.resolve().is_relative_to(root):
        raise ValueError('Target escapes project or uses a link: ' + str(target))
    for path in (target, *target.parents):
        if path.is_symlink() or path.is_junction():
            raise ValueError('Linked install path: ' + str(path))
        if path == root:
            break
    if target.is_dir():
        if any(p.is_symlink() or p.is_junction() for p in target.rglob('*')):
            raise ValueError('Linked contents in managed directory')
    return target


def move_checked(source, target):
    # Windows file watchers can briefly retain a handle immediately after rename.
    # Retry only an absent destination; never replace a concurrently created path.
    for attempt in range(5):
        if target.exists():
            raise FileExistsError(str(target))
        try:
            source.rename(target)
            return
        except PermissionError:
            if attempt == 4 or not source.exists() or target.exists():
                raise
            time.sleep(0.1 * (attempt + 1))


def install(archive, project, install_id):
    archive_bytes = Path(archive).read_bytes()
    payload = read_zip_bytes(archive_bytes)
    verification = verify_payload(payload, archive_bytes)
    if not install_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in install_id):
        raise ValueError('install-id must contain ASCII letters/digits/hyphen/underscore')
    project = Path(project).resolve(strict=True)
    backup = checked_path(project, 'artifacts/bob-distribution-backups/' + install_id)
    if backup.exists():
        raise ValueError('Install ID already exists')
    targets = {name: checked_path(project, name) for name in MANAGED}
    backup.mkdir(parents=True)
    staging = backup / 'staged'
    for name, data in payload.items():
        if name.startswith('.bob/'):
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    moved, installed = [], []
    previous = {}
    try:
        for name, target in targets.items():
            if target.exists():
                files = sorted(p for p in target.rglob('*') if p.is_file()) if target.is_dir() else [target]
                previous[name] = {p.relative_to(project).as_posix(): sha(p.read_bytes()) for p in files}
                saved = backup / 'previous' / name
                saved.parent.mkdir(parents=True, exist_ok=True)
                move_checked(target, saved)
                moved.append((target, saved))
            target.parent.mkdir(parents=True, exist_ok=True)
            move_checked(staging / name, target)
            installed.append(target)
        for name, data in payload.items():
            if name.startswith('.bob/') and (project / name).read_bytes() != data:
                raise ValueError('Installed byte mismatch: ' + name)
    except Exception:
        for target in reversed(installed):
            saved = backup / 'failed-new' / target.relative_to(project)
            saved.parent.mkdir(parents=True, exist_ok=True)
            move_checked(target, saved)
        for target, saved in reversed(moved):
            move_checked(saved, target)
        raise
    receipt = {'status': 'passed', 'archive': str(Path(archive).resolve()),
               'archive_sha256': verification['sha256'], 'project': str(project),
               'backup': str(backup), 'previous': previous,
               'installed': {name: sha(data) for name, data in payload.items() if name.startswith('.bob/')},
               'bob_chat_skill_activation': 'not_tested'}
    (backup / 'installation.json').write_bytes(encoded(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('build')
    check = commands.add_parser('verify')
    check.add_argument('--archive', type=Path, required=True)
    deploy = commands.add_parser('install')
    deploy.add_argument('--archive', type=Path, required=True)
    deploy.add_argument('--project', type=Path, required=True)
    deploy.add_argument('--install-id', required=True)
    args = parser.parse_args()
    if args.command == 'build':
        result = build()
    elif args.command == 'verify':
        result = verify(args.archive)
    else:
        result = install(args.archive, args.project, args.install_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
