"""Maintainer-only release sealing and bundling. Not shipped inside the skill."""
from pathlib import Path
import argparse
import hashlib
import json
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/routine-spec-doc'
VERSION = '0.1.0'
FILES = ['SKILL.md', 'scripts/specflow.py', 'scripts/_engine.py',
         'assets/examples/alarm_qualification.json', 'assets/schema/routine-spec.schema.json',
         'assets/templates/routine-spec-v01.docx', 'references/authoring.md', 'requirements.txt']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seal():
    release = {'name': 'routine-spec-kit', 'version': VERSION,
               'profile_id': 'alarm-qualification-v01', 'routine_id': 'RTN-ALM-001',
               'template_id': 'routine-spec-v01',
               'schema': 'assets/schema/routine-spec.schema.json',
               'template': 'assets/templates/routine-spec-v01.docx',
               'example': 'assets/examples/alarm_qualification.json',
               'runtime': {'python_minor': '3.12', 'dependencies': {'python-docx': '1.2.0', 'lxml': '6.1.1'}},
               'limits': ['10-cycle continuous-ON sample only', 'draft_trial only',
                          'Limited JSON Schema keyword validator', 'No visual rendering or RTOS validation'],
               'files': {name: sha(SKILL / name) for name in FILES}}
    (SKILL / 'release.json').write_text(json.dumps(release, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'sealed', 'release_sha256': sha(SKILL / 'release.json')}))


def bundle():
    release_path = SKILL / 'release.json'
    release = json.loads(release_path.read_text(encoding='utf-8'))
    if release['version'] != VERSION or set(release['files']) != set(FILES):
        raise ValueError('Release identity or resource inventory mismatch')
    for name, expected in release['files'].items():
        if sha(SKILL / name) != expected:
            raise ValueError(f'Unsealed resource: {name}')
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    target = dist / f'routine-spec-kit-{VERSION}.zip'
    # The consumer bundle intentionally excludes maintainer tools, tests and QA.
    files = [ROOT / 'README.md'] + [SKILL / name for name in FILES + ['release.json']]
    with ZipFile(target, 'w', compression=ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(files):
            name = 'routine-spec-kit/' + path.relative_to(ROOT).as_posix()
            info = ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, path.read_bytes())
    record = {'file': target.name, 'sha256': sha(target), 'bytes': target.stat().st_size,
              'release_sha256': sha(release_path), 'file_count': len(files)}
    (dist / 'checksums.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['seal', 'bundle'])
    args = parser.parse_args()
    seal() if args.command == 'seal' else bundle()
