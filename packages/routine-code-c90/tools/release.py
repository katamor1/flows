"""Maintainer-only deterministic Bob skill release and ZIP creation."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/routine-code-c90'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def seal():
    paths = sorted(p for p in SKILL.rglob('*') if p.is_file() and p.name != 'release.json')
    if any('__pycache__' in p.parts for p in paths):
        raise ValueError('Unexpected bytecode in package')
    record = {'name': 'routine-code-c90', 'version': '0.1.0',
              'profile': 'alarm-qualification-v01',
              'spec_sha256': sha((SKILL / 'assets/alarm-profile/input/spec.json').read_bytes()),
              'files': {p.relative_to(SKILL).as_posix(): sha(p.read_bytes()) for p in paths}}
    (SKILL / 'release.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'sealed', 'release_sha256': sha((SKILL / 'release.json').read_bytes())}))


def bundle():
    release_bytes = (SKILL / 'release.json').read_bytes()
    release = json.loads(release_bytes)
    actual = {p.relative_to(SKILL).as_posix() for p in SKILL.rglob('*') if p.is_file()}
    if actual != set(release['files']) | {'release.json'}:
        raise ValueError('Package inventory differs from release')
    payload = {}
    for name, expected in release['files'].items():
        content = (SKILL / name).read_bytes()
        if sha(content) != expected:
            raise ValueError('Unsealed resource: ' + name)
        payload['.bob/skills/routine-code-c90/' + name] = content
    payload['.bob/skills/routine-code-c90/release.json'] = release_bytes
    payload['BOB-TEAM-README.md'] = (ROOT / 'README.md').read_bytes()
    payload['distribution.json'] = (json.dumps({
        'name': 'routine-code-c90', 'version': '0.1.0', 'bob_ide_execution': 'not_tested',
        'release_sha256': sha(release_bytes),
        'files': {name: sha(data) for name, data in sorted(payload.items())}}, indent=2) + '\n').encode('utf-8')
    path = ROOT / 'dist/ibm-bob-routine-code-c90-0.1.0.zip'
    path.parent.mkdir(exist_ok=True)
    with ZipFile(path, 'w', compression=ZIP_DEFLATED) as archive:
        for name, data in sorted(payload.items()):
            info = ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with ZipFile(path) as archive:
        if archive.testzip() is not None or any(archive.read(name) != data for name, data in payload.items()):
            raise ValueError('ZIP readback failed')
    receipt = {'archive': path.name, 'sha256': sha(path.read_bytes()),
               'size_bytes': path.stat().st_size, 'entry_count': len(payload), 'readback': 'passed'}
    (path.parent / 'checksums.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['seal', 'bundle'])
    args = parser.parse_args()
    seal() if args.command == 'seal' else bundle()
