import shutil
import unittest
from zipfile import ZipFile
from _support import PACKAGE, OFFICE, CODE_JOB, new_test_root, cli, load


@unittest.skipUnless(OFFICE, 'Set UT_OFFICECLI to the approved executable')
class DistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = new_test_root('distribution-')
        archive = PACKAGE / 'dist/ibm-bob-routine-unit-test-officecli-0.1.0.zip'
        with ZipFile(archive) as z:
            for name in z.namelist():
                if not (cls.root / name).resolve().is_relative_to(cls.root):
                    raise RuntimeError('Unexpected archive path')
            z.extractall(cls.root)
        cls.skill = cls.root / '.bob/skills/routine-unit-test-spec'

    def test_forward_execution(self):
        result = cli(self.skill, 'doctor')
        self.assertEqual(result.returncode, 0, result.stderr)
        result = cli(self.skill, 'new-job', '--code-job', CODE_JOB,
                     '--workspace', self.root / 'jobs', '--job', 'forward')
        self.assertEqual(result.returncode, 0, result.stderr)
        result = cli(self.skill, 'render', '--workspace', self.root / 'jobs',
                     '--job', 'forward', '--run', 'r001')
        self.assertEqual(result.returncode, 0, result.stderr)
        check = load(self.root / 'jobs/forward/renders/r001/content-check.json')
        self.assertEqual(check['status'], 'passed')

    def test_package_change_rejected(self):
        target = self.skill / 'SKILL.md'
        original = target.read_bytes()
        target.write_bytes(original + b'\n')
        try:
            result = cli(self.skill, 'doctor')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('hash mismatch', result.stderr)
        finally:
            target.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
