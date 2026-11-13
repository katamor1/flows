"""Consumer-level checks; run against copied releases, never mutate the release."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/routine-spec-doc'
REFERENCE = ROOT.parents[1] / 'prototypes/routine-spec-flow/output/PS-RTN-ALM-001.docx'


class PackageTests(unittest.TestCase):
    def setUp(self):
        temp_root = ROOT / 'qa/temp'
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        self.base = Path(self.temp.name)
        self.skill = self.base / 'distribution/routine-spec-doc'
        if SKILL.exists():
            shutil.copytree(SKILL, self.skill)
        self.workspace = self.base / '案件 data'

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, command, *args, ok=True):
        p = subprocess.run([sys.executable, '-B', str(self.skill / 'scripts/specflow.py'),
                            command, *map(str, args)], capture_output=True, text=True,
                           encoding='utf-8', env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
            return json.loads(p.stdout)
        self.assertNotEqual(p.returncode, 0, p.stdout)
        return p

    def job_args(self, job='alarm-01'):
        return ['--workspace', self.workspace, '--job', job]

    def new(self):
        return self.cli('new-job', *self.job_args())

    def test_doctor_and_profile(self):
        self.assertEqual(self.cli('doctor')['status'], 'ok')
        self.assertEqual(self.cli('describe')['profile_id'], 'alarm-qualification-v01')

    def test_roundtrip_deterministic_and_reference_unchanged(self):
        before = {p.relative_to(self.skill).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.skill.rglob('*') if p.is_file()}
        self.new()
        self.assertEqual(self.cli('validate', *self.job_args())['status'], 'valid')
        first = self.cli('render', *self.job_args(), '--run', 'r001')
        second = self.cli('render', *self.job_args(), '--run', 'r002')
        a, b = Path(first['document']), Path(second['document'])
        self.assertEqual(a.read_bytes(), b.read_bytes())
        self.assertEqual(a.read_bytes(), REFERENCE.read_bytes())
        manifest = json.loads(Path(first['manifest']).read_text(encoding='utf-8'))
        self.assertEqual(manifest['package']['version'], '0.1.0')
        self.assertEqual(manifest['source_sha256'], hashlib.sha256((a.parent / 'spec.json').read_bytes()).hexdigest())
        after = {p.relative_to(self.skill).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.skill.rglob('*') if p.is_file()}
        self.assertEqual(before, after, 'Normal execution changed package resources')

    def test_existing_job_and_run_refused(self):
        self.new()
        source = self.workspace / 'alarm-01/source/spec.json'
        source.write_text(source.read_text(encoding='utf-8') + '\n', encoding='utf-8')
        before = source.read_bytes()
        self.cli('new-job', *self.job_args(), ok=False)
        self.assertEqual(source.read_bytes(), before)
        first = self.cli('render', *self.job_args(), '--run', 'r001')
        doc = Path(first['document'])
        before = doc.read_bytes()
        self.cli('render', *self.job_args(), '--run', 'r001', ok=False)
        self.assertEqual(doc.read_bytes(), before)

    def test_missing_or_modified_asset_refused(self):
        template = self.skill / 'assets/templates/routine-spec-v01.docx'
        self.assertTrue(template.exists(), 'Frozen template not packaged')
        template.write_bytes(template.read_bytes() + b'change')
        self.cli('doctor', ok=False)
        self.cli('new-job', *self.job_args(), ok=False)
        template.unlink()
        self.cli('doctor', ok=False)
        self.assertFalse(self.workspace.exists())

    def test_package_paths_and_traversal_refused(self):
        self.cli('new-job', '--workspace', self.skill / 'jobs', '--job', 'alarm', ok=False)
        self.cli('new-job', '--workspace', self.workspace, '--job', '../escape', ok=False)
        self.new()
        self.cli('render', *self.job_args(), '--run', '../escape', ok=False)

    def test_job_link_outside_workspace_refused(self):
        self.workspace.mkdir(parents=True)
        outside = self.base / 'outside'
        outside.mkdir()
        link = self.workspace / 'alarm-01'
        if os.name == 'nt':
            p = subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(link), str(outside)],
                               capture_output=True)
            if p.returncode != 0 and b'Access is denied' in p.stdout + p.stderr:
                self.skipTest('Sandbox denies creating Windows junctions')
            self.assertEqual(p.returncode, 0, 'Cannot create test junction: ' + repr(p.stdout + p.stderr))
        else:
            link.symlink_to(outside, target_is_directory=True)
        self.cli('validate', *self.job_args(), ok=False)
        self.assertFalse(list(outside.iterdir()))

    def test_lock_mismatch_refused(self):
        self.new()
        lock = self.workspace / 'alarm-01/package-lock.json'
        data = json.loads(lock.read_text(encoding='utf-8'))
        data['release_sha256'] = '0' * 64
        lock.write_text(json.dumps(data), encoding='utf-8')
        self.cli('render', *self.job_args(), '--run', 'r001', ok=False)
        self.assertFalse((self.workspace / 'alarm-01/renders/r001').exists())

    def test_invalid_source_not_published(self):
        self.new()
        source = self.workspace / 'alarm-01/source/spec.json'
        data = json.loads(source.read_text(encoding='utf-8'))
        data['behavior']['threshold'] = 12
        source.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        self.cli('validate', *self.job_args(), ok=False)
        self.cli('render', *self.job_args(), '--run', 'r001', ok=False)
        self.assertFalse((self.workspace / 'alarm-01/renders/r001').exists())

    def test_no_initialization_or_overrides_exposed(self):
        for command in ('init-schema', 'template'):
            self.cli(command, ok=False)
        self.cli('render', *self.job_args(), '--run', 'r001', '--template', 'other.docx', ok=False)

    def test_generation_failure_leaves_no_output_or_lock_and_can_retry(self):
        self.new()
        source = self.workspace / 'alarm-01/source/spec.json'
        original = source.read_bytes()
        data = json.loads(original)
        data['document']['title'] = '{{unexpected-token}}'
        source.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        self.cli('render', *self.job_args(), '--run', 'r001', ok=False)
        renders = self.workspace / 'alarm-01/renders'
        self.assertEqual(list(renders.iterdir()), [])
        source.write_bytes(original)
        self.cli('render', *self.job_args(), '--run', 'r001')

    def test_dependency_mismatch_refused(self):
        path = self.skill / 'release.json'
        release = json.loads(path.read_text(encoding='utf-8'))
        release['runtime']['dependencies']['python-docx'] = '0.0.0'
        path.write_text(json.dumps(release), encoding='utf-8')
        result = self.cli('doctor', ok=False)
        self.assertIn('Dependency mismatch', result.stderr)

    def test_optimized_maintainer_bundle_rejects_changed_resources(self):
        checkout = self.base / 'maintainer'
        skill = checkout / 'skills/routine-spec-doc'
        shutil.copytree(self.skill, skill)
        (checkout / 'tools').mkdir()
        shutil.copyfile(ROOT / 'tools/release.py', checkout / 'tools/release.py')
        (checkout / 'README.md').write_text('Consumer documentation', encoding='utf-8')
        template = skill / 'assets/templates/routine-spec-v01.docx'
        template.write_bytes(template.read_bytes() + b'changed')
        result = subprocess.run([sys.executable, '-B', '-O', str(checkout / 'tools/release.py'), 'bundle'],
                                capture_output=True)
        self.assertNotEqual(result.returncode, 0, 'Optimized Python bundled changed resources')
        self.assertFalse((checkout / 'dist').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
