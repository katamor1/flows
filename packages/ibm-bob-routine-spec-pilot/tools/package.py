"""Maintainer packaging only: relocate verified resources without regenerating them."""
from pathlib import Path
import hashlib
import json
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'routine-spec-kit/skills/routine-spec-doc'
EXPECTED_RELEASE = '2e4d8621b8143f04b9853849c69860f33abcb009f0e133c8c0b1e4c9ceb5dd1b'


def sha(content):
    return hashlib.sha256(content).hexdigest()


def main():
    release_bytes = (SOURCE / 'release.json').read_bytes()
    if sha(release_bytes) != EXPECTED_RELEASE:
        raise ValueError('Unapproved source release; review before changing the Bob distribution')
    release = json.loads(release_bytes)
    payload = {}
    for name, expected in release['files'].items():
        content = (SOURCE / name).read_bytes()
        if sha(content) != expected:
            raise ValueError(f'Source resource hash mismatch: {name}')
        payload['.bob/skills/routine-spec-doc/' + name] = content
    payload['.bob/skills/routine-spec-doc/release.json'] = release_bytes
    payload['.bob/rules/20-routine-spec.md'] = (ROOT / 'content/20-routine-spec.md').read_bytes()
    payload['BOB-TEAM-README.md'] = (ROOT / 'README.md').read_bytes()
    distribution = {
        'name': 'ibm-bob-routine-spec-pilot', 'version': '0.1.0',
        'status': 'candidate_for_team_acceptance',
        'layout': 'IBM Bob project skills and rules',
        'runtime_release_sha256': EXPECTED_RELEASE,
        'generator_backend': 'unchanged Python routine-spec-kit 0.1.0',
        'office_integration': 'Bob built-in office_read for read and validate; requires Bob acceptance',
        'bob_ide_tested_build': None,
        'bundled_officecli_tested_version': None,
        'files': {name: sha(content) for name, content in sorted(payload.items())},
    }
    payload['distribution.json'] = (json.dumps(distribution, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    archive = dist / 'ibm-bob-routine-spec-pilot-0.1.0.zip'
    with ZipFile(archive, 'w', compression=ZIP_DEFLATED, compresslevel=9) as z:
        for name, content in sorted(payload.items()):
            info = ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, content)
    record = {'file': archive.name, 'sha256': sha(archive.read_bytes()),
              'bytes': archive.stat().st_size, 'file_count': len(payload),
              'runtime_release_sha256': EXPECTED_RELEASE}
    (dist / 'checksums.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
