"""Verify the Bob layout and unchanged runtime from a freshly extracted ZIP."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT.parent / 'routine-spec-kit/skills/routine-spec-doc'


class BobDistributionTest(unittest.TestCase):
    def test_archive_layout_and_runtime_relocation(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/package.py')],
                                capture_output=True, text=True, encoding='utf-8',
                                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(result.stdout)
        archive = ROOT / 'dist' / record['file']
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), record['sha256'])
        temp_root = ROOT / 'qa'
        temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as temp:
            project = Path(temp) / 'pilot-project'
            with ZipFile(archive) as z:
                names = z.namelist()
                self.assertIn('.bob/skills/routine-spec-doc/SKILL.md', names)
                self.assertIn('.bob/rules/20-routine-spec.md', names)
                self.assertNotIn('.bob/settings.json', names)
                self.assertFalse(any('officecli.exe' in name or 'plugin.json' in name for name in names))
                z.extractall(project)
            skill = project / '.bob/skills/routine-spec-doc'
            release = json.loads((skill / 'release.json').read_text(encoding='utf-8'))
            for name, expected in release['files'].items():
                self.assertEqual((skill / name).read_bytes(), (RUNTIME / name).read_bytes())
                self.assertEqual(hashlib.sha256((skill / name).read_bytes()).hexdigest(), expected)
            args = ['--workspace', str(project / 'spec-jobs'), '--job', 'bob-pilot-01']
            replies = []
            for command, extra in [('doctor', []), ('new-job', args), ('validate', args),
                                   ('render', args + ['--run', 'r001'])]:
                p = subprocess.run([sys.executable, '-B', str(skill / 'scripts/specflow.py'), command, *extra],
                                   capture_output=True, text=True, encoding='utf-8',
                                   env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
                self.assertEqual(p.returncode, 0, p.stderr)
                replies.append(json.loads(p.stdout))
            document = Path(replies[-1]['document'])
            self.assertEqual(hashlib.sha256(document.read_bytes()).hexdigest(),
                             '99f478ddc1f1f54bae1b1f003e401bf92d3bd20471349e654cfc466b8220667f')
            for name, expected in release['files'].items():
                self.assertEqual(hashlib.sha256((skill / name).read_bytes()).hexdigest(), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
