"""Maintainer-only release sealing and Bob layout packaging."""
from pathlib import Path
import argparse
import hashlib
import json
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'skills/routine-spec-doc'
FILES = ['SKILL.md', 'scripts/specflow.py', 'scripts/_renderer.py', 'scripts/_contract.py',
         'assets/schema/routine-spec.schema.json', 'assets/examples/alarm_qualification.json',
         'assets/templates/routine-spec-v01.docx', 'references/authoring.md', 'requirements.txt']


def sha(content):
    return hashlib.sha256(content).hexdigest()


def seal():
    release = {'name': 'routine-spec-officecli', 'version': '0.2.0', 'profile_id': 'alarm-qualification-v01',
               'routine_id': 'RTN-ALM-001', 'template_id': 'routine-spec-v01', 'template_revision': '0.2.0',
               'schema': 'assets/schema/routine-spec.schema.json',
               'example': 'assets/examples/alarm_qualification.json',
               'template': 'assets/templates/routine-spec-v01.docx',
               'officecli': {'version': '1.0.144', 'sha256': 'eec03daa7978a1e8f28a4ee0ce910ef9e3cb355d26a7fa4afcecadfe34693fbb'},
               'limits': ['10-cycle alarm qualification draft profile only', 'Python 3.12 standard library',
                          'Approved Windows OfficeCLI binary required', 'No automatic visual approval or RTOS testing'],
               'files': {name: sha((SKILL/name).read_bytes()) for name in FILES}}
    (SKILL/'release.json').write_text(json.dumps(release, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': 'sealed', 'release_sha256': sha((SKILL/'release.json').read_bytes())}))


def bundle():
    release_bytes = (SKILL/'release.json').read_bytes()
    release = json.loads(release_bytes)
    if set(release['files']) != set(FILES):
        raise ValueError('Resource inventory mismatch')
    payload = {}
    for name, expected in release['files'].items():
        content = (SKILL/name).read_bytes()
        if sha(content) != expected:
            raise ValueError('Unsealed resource: '+name)
        payload['.bob/skills/routine-spec-doc/'+name] = content
    payload['.bob/skills/routine-spec-doc/release.json'] = release_bytes
    payload['.bob/rules/20-routine-spec.md'] = (ROOT/'content/20-routine-spec.md').read_bytes()
    payload['BOB-TEAM-README.md'] = (ROOT/'README.md').read_bytes()
    metadata = {'name': 'routine-spec-officecli', 'version': '0.2.0',
                'generator_backend': 'OfficeCLI', 'python_dependencies': 'standard library only',
                'release_sha256': sha(release_bytes), 'tested_officecli': release['officecli'],
                'observed_bob_ide': '2.2.3', 'bob_chat_skill_activation': 'not_tested',
                'files': {name: sha(content) for name, content in sorted(payload.items())}}
    payload['distribution.json'] = (json.dumps(metadata, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    dist = ROOT/'dist'
    dist.mkdir(exist_ok=True)
    target = dist/'ibm-bob-routine-spec-officecli-0.2.0.zip'
    with ZipFile(target, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(payload.items()):
            item = ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            item.compress_type = ZIP_DEFLATED
            item.external_attr = 0o644 << 16
            archive.writestr(item, content)
    record = {'file': target.name, 'sha256': sha(target.read_bytes()), 'bytes': target.stat().st_size,
              'files': len(payload), 'release_sha256': sha(release_bytes)}
    (dist/'checksums.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(record))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['seal', 'bundle'])
    args = parser.parse_args()
    seal() if args.command == 'seal' else bundle()
