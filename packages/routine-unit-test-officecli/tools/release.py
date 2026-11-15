"""Maintainer-only release sealing and IBM Bob team ZIP packaging."""
from pathlib import Path
import argparse
import hashlib
import json
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'skills/routine-unit-test-spec'
FILES = ['SKILL.md', 'scripts/utflow.py', 'scripts/_renderer.py', 'scripts/_contract.py',
         'assets/schema/unit-test-spec.schema.json', 'assets/examples/alarm_unit_test.json',
         'assets/templates/unit-test-spec-v01.docx', 'references/authoring.md', 'requirements.txt']
VERSION = '0.1.0'
INPUT_FILES = {
    'inputs/program-spec.json': '097b1185e284c17805b51c92dd821d1bec64f55d0ce1781c2c1fb369239b4265',
    'inputs/AlarmQualification.c': 'e2b910d6aaf0932a19c3f287cb6513a5193a9e365435c5876a29cd7684683bee',
    'inputs/AlarmQualification.h': '3f8799a676201b23a2fa96e7eddfaf4fe99a67429edb2e460571197a238bcf00',
}


def sha(content):
    return hashlib.sha256(content).hexdigest()


def seal():
    actual = {path.relative_to(SKILL).as_posix() for path in SKILL.rglob('*') if path.is_file()}
    if actual - {'release.json'} != set(FILES):
        raise ValueError('Missing or unexpected skill resources')
    release = {'name': 'routine-unit-test-officecli', 'version': VERSION,
               'profile_id': 'alarm-qualification-unit-test-v01', 'routine_id': 'RTN-ALM-001',
               'template_id': 'unit-test-spec-v01', 'template_revision': VERSION,
               'schema': 'assets/schema/unit-test-spec.schema.json',
               'example': 'assets/examples/alarm_unit_test.json',
               'template': 'assets/templates/unit-test-spec-v01.docx',
               'input_files': INPUT_FILES,
               'target': {'program_spec_sha256': INPUT_FILES['inputs/program-spec.json'],
                          'source_sha256': INPUT_FILES['inputs/AlarmQualification.c'],
                          'header_sha256': INPUT_FILES['inputs/AlarmQualification.h']},
               'officecli': {'version': '1.0.144', 'sha256': 'eec03daa7978a1e8f28a4ee0ce910ef9e3cb355d26a7fa4afcecadfe34693fbb'},
               'limits': ['Frozen AlarmQualification_Update program/C90 draft profile only',
                          'Python 3.12 standard library', 'Approved Windows OfficeCLI binary required',
                          'All test and review items remain not_executed',
                          'No dynamic test runner, automatic visual approval, RTOS validation or requirement approval'],
               'files': {name: sha((SKILL/name).read_bytes()) for name in FILES}}
    (SKILL/'release.json').write_text(json.dumps(release, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': 'sealed', 'release_sha256': sha((SKILL/'release.json').read_bytes())}))


def bundle():
    release_bytes = (SKILL/'release.json').read_bytes()
    release = json.loads(release_bytes)
    actual = {path.relative_to(SKILL).as_posix() for path in SKILL.rglob('*') if path.is_file()}
    if set(release['files']) != set(FILES) or actual != set(FILES)|{'release.json'}:
        raise ValueError('Resource inventory mismatch')
    payload = {}
    for name, expected in release['files'].items():
        content = (SKILL/name).read_bytes()
        if sha(content) != expected:
            raise ValueError('Unsealed resource: '+name)
        payload['.bob/skills/routine-unit-test-spec/'+name] = content
    payload['.bob/skills/routine-unit-test-spec/release.json'] = release_bytes
    payload['.bob/rules/30-routine-unit-test-spec.md'] = (ROOT/'content/30-routine-unit-test-spec.md').read_bytes()
    payload['BOB-TEAM-README.md'] = (ROOT/'README.md').read_bytes()
    metadata = {'name': release['name'], 'version': release['version'], 'generator_backend': 'OfficeCLI',
                'python_dependencies': 'standard library only', 'release_sha256': sha(release_bytes),
                'pinned_officecli': release['officecli'], 'bob_chat_skill_activation': 'not_tested',
                'test_execution': 'not_executed',
                'files': {name: sha(content) for name, content in sorted(payload.items())}}
    payload['distribution.json'] = (json.dumps(metadata, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    dist = ROOT/'dist'
    dist.mkdir(exist_ok=True)
    target = dist/f'ibm-bob-routine-unit-test-officecli-{VERSION}.zip'
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
