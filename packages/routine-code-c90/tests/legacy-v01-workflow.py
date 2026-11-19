import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
SKILL = PACKAGE / 'skills/routine-code-c90'
WORKSPACE = PACKAGE.parents[1]


def cli(*args):
    return subprocess.run([sys.executable, '-X', 'utf8', '-S', '-B', str(SKILL / 'scripts/codegen.py'),
                           *map(str, args)], capture_output=True, text=True, encoding='utf-8', timeout=30)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        parent = WORKSPACE / 'artifacts/routine-code-skill/tool-tests'
        parent.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=parent)).resolve()
        self.spec = SKILL / 'assets/alarm-profile/input/spec.json'

    def prepare(self):
        result = cli('prepare', '--spec', self.spec, '--workspace', self.root, '--job', 'case')
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.root / 'case'

    def test_prepared_case_has_no_answer_and_assets_are_identical(self):
        job = self.prepare()
        self.assertFalse((job / 'src/AlarmQualification.c').exists())
        self.assertEqual((job / 'tools/codeflow.py').read_bytes(),
                         (WORKSPACE / 'prototypes/routine-code-poc/tools/codeflow.py').read_bytes())
        self.assertFalse((job / 'records/pending.json').exists())

    def test_changed_spec_rejected(self):
        changed = self.root / 'different.json'
        changed.write_bytes(self.spec.read_bytes() + b'\n')
        result = cli('prepare', '--spec', changed, '--workspace', self.root, '--job', 'case')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'case').exists())

    def test_existing_job_rejected_without_leaving_lock(self):
        self.prepare()
        result = cli('prepare', '--spec', self.spec, '--workspace', self.root, '--job', 'case')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / '.case.lock').exists())

    def test_fixed_test_change_rejected(self):
        job = self.prepare()
        with (job / 'tests/test_alarm_qualification.c').open('a') as output:
            output.write('\n')
        result = cli('record', '--workspace', self.root, '--job', 'case', '--generation', 'g001',
                     '--agent', 'Codex', '--agent-version', 'test', '--bob-executed', 'no', '--note', 'guard test')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Fixed job asset changed', result.stderr)

    def test_traversal_id_rejected(self):
        result = cli('prepare', '--spec', self.spec, '--workspace', self.root, '--job', '../escape')
        self.assertNotEqual(result.returncode, 0)

    def test_missing_traceability_rejected(self):
        job = self.prepare()
        (job / 'src/AlarmQualification.c').write_text('/* test-only draft */\n', encoding='ascii')
        result = cli('record', '--workspace', self.root, '--job', 'case', '--generation', 'g001',
                     '--agent', 'Codex', '--agent-version', 'test', '--bob-executed', 'no', '--note', 'guard test')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('traceability.md', result.stderr)

    def test_generation_records_are_not_overwritten(self):
        job = self.prepare()
        (job / 'src/AlarmQualification.c').write_text('/* test-only draft, not verified */\n', encoding='ascii')
        (job / 'traceability.md').write_text('Test-only mapping; no success claim.\n', encoding='utf-8')
        args = ['record', '--workspace', self.root, '--job', 'case', '--generation', 'g001',
                '--agent', 'Codex', '--agent-version', 'test', '--bob-executed', 'no', '--note', 'record-only test']
        first = cli(*args)
        self.assertEqual(first.returncode, 0, first.stderr)
        before = (job / 'records/g001.json').read_bytes()
        second = cli(*args)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(before, (job / 'records/g001.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
