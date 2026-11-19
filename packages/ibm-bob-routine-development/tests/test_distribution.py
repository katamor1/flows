"""Exercise combined integrity, contained targets and reversible upgrade behavior."""
import importlib.util
import json
from pathlib import Path
import unittest
import uuid
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('manager', ROOT / 'tools/manage.py')
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)


class DistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive = ROOT / 'dist/ibm-bob-routine-development-0.1.0.zip'
        cls.payload = manager.read_zip(cls.archive)
        cls.work = ROOT.parents[1] / 'artifacts/routine-generic-validation/distribution-tests' / uuid.uuid4().hex
        cls.work.mkdir(parents=True)

    def make_zip(self, name, payload):
        target = self.work / name
        with ZipFile(target, 'w') as archive:
            for path, data in payload.items():
                archive.writestr(path, data)
        return target

    def test_sealed_three_kit_inventory(self):
        result = manager.verify(self.archive)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(len(result['skills']), 3)

    def test_tampered_skill_rejected(self):
        payload = dict(self.payload)
        payload['.bob/skills/routine-code-c90/scripts/codegen.py'] += b'\n# tampered\n'
        archive = self.make_zip('tampered.zip', payload)
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            manager.verify(archive)

    def test_traversal_and_duplicate_entries_rejected(self):
        unsafe = self.make_zip('unsafe.zip', {'../escape.txt': b'bad'})
        with self.assertRaisesRegex(ValueError, 'Unsafe ZIP entry'):
            manager.read_zip(unsafe)
        duplicate = self.work / 'duplicate.zip'
        with ZipFile(duplicate, 'w') as archive:
            archive.writestr('same.txt', b'a')
            archive.writestr('same.txt', b'b')
        with self.assertRaisesRegex(ValueError, 'Duplicate ZIP entries'):
            manager.read_zip(duplicate)

    def test_upgrade_preserves_previous_and_unrelated_files(self):
        project = self.work / 'project'
        old = project / '.bob/skills/routine-code-c90'
        old.mkdir(parents=True)
        (old / 'obsolete.py').write_bytes(b'previous custom resource\r\n')
        unrelated = project / '.bob/rules/team.md'
        unrelated.parent.mkdir(parents=True)
        unrelated.write_bytes(b'keep team rule\n')
        result = manager.install(self.archive, project, 'upgrade-001')
        self.assertEqual(result['status'], 'passed')
        self.assertFalse((old / 'obsolete.py').exists())
        saved = Path(result['backup']) / 'previous/.bob/skills/routine-code-c90/obsolete.py'
        self.assertEqual(saved.read_bytes(), b'previous custom resource\r\n')
        self.assertEqual(unrelated.read_bytes(), b'keep team rule\n')
        for name, data in self.payload.items():
            if name.startswith('.bob/'):
                self.assertEqual((project / name).read_bytes(), data)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            manager.install(self.archive, project, 'upgrade-001')

    def test_install_id_and_target_containment(self):
        project = self.work / 'containment'
        project.mkdir()
        with self.assertRaisesRegex(ValueError, 'install-id'):
            manager.install(self.archive, project, '../bad')
        with self.assertRaisesRegex(ValueError, 'escapes'):
            manager.checked_path(project.resolve(), '../outside')
        self.assertFalse((project / '.bob').exists())

    def test_move_retries_transient_permission_error_without_replacing_target(self):
        source = self.work / 'move-source.txt'
        target = self.work / 'move-target.txt'
        source.write_bytes(b'new')
        original = Path.rename
        calls = []

        def transient(path, destination):
            calls.append(path)
            if len(calls) == 1:
                raise PermissionError('transient watcher handle')
            return original(path, destination)

        with patch.object(Path, 'rename', transient):
            manager.move_checked(source, target)
        self.assertEqual(target.read_bytes(), b'new')
        self.assertEqual(len(calls), 2)
        source.write_bytes(b'another')
        with self.assertRaises(FileExistsError):
            manager.move_checked(source, target)
        self.assertEqual(target.read_bytes(), b'new')

    def test_install_uses_verified_snapshot_when_archive_is_replaced(self):
        changing = self.make_zip('changing.zip', self.payload)
        original_sha = manager.sha(changing.read_bytes())
        project = self.work / 'snapshot-project'
        project.mkdir()
        original_verify = manager.verify_payload
        original_code = self.payload['.bob/skills/routine-code-c90/scripts/codegen.py']

        def replace_after_verification(payload, archive_bytes):
            result = original_verify(payload, archive_bytes)
            tampered = dict(self.payload)
            tampered['.bob/skills/routine-code-c90/scripts/codegen.py'] = b'not verified'
            self.make_zip('changing.zip', tampered)
            return result

        with patch.object(manager, 'verify_payload', replace_after_verification):
            result = manager.install(changing, project, 'snapshot-001')
        self.assertEqual(result['archive_sha256'], original_sha)
        self.assertNotEqual(manager.sha(changing.read_bytes()), original_sha)
        self.assertEqual((project / '.bob/skills/routine-code-c90/scripts/codegen.py').read_bytes(), original_code)


if __name__ == '__main__':
    unittest.main(verbosity=2)
