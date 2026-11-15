import unittest
from _support import SKILL, OFFICE, CODE_JOB, new_test_root, cli, load, save


@unittest.skipUnless(OFFICE, 'Set UT_OFFICECLI to the approved executable')
class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = new_test_root('render-')
        created = cli(SKILL, 'new-job', '--code-job', CODE_JOB,
                      '--workspace', cls.root, '--job', 'sample')
        if created.returncode:
            raise RuntimeError(created.stderr)
        cls.job = cls.root / 'sample'

    def run_cli(self, *args):
        return cli(SKILL, *args, '--workspace', self.root, '--job', 'sample')

    def test_render_roundtrip_and_same_input_reproduction(self):
        source = self.job / 'source/unit-test-spec.json'
        data = load(source)
        data['summary'] += '\n差込文字の検査: {{literal}}\n改行の保持と日本語表示を確認する。' + '長文の折返し確認。' * 20
        save(source, data)
        try:
            for run in ('same-a', 'same-b'):
                result = self.run_cli('render', '--run', run)
                self.assertEqual(result.returncode, 0, result.stderr)
                check = load(self.job / 'renders' / run / 'content-check.json')
                self.assertEqual(check['status'], 'passed')
                manifest = load(self.job / 'renders' / run / 'manifest.json')
                self.assertEqual(manifest['status'], 'draft_trial')
                trace = load(self.job / 'renders' / run / 'traceability.json')
                self.assertEqual(trace['counts']['representative_cases'], 16)
                self.assertEqual(trace['families'][-1]['call_checks'], 1948617)
                record = load(self.job / 'renders' / run / 'execution-record.json')
                self.assertTrue(all(x['status'] == 'not_executed' for x in record['results']))
            first = load(self.job / 'renders/same-a/content-check.json')
            second = load(self.job / 'renders/same-b/content-check.json')
            self.assertEqual(first['semantic_sha256'], second['semantic_sha256'])
            again = self.run_cli('render', '--run', 'same-a')
            self.assertNotEqual(again.returncode, 0)
        finally:
            original = load(SKILL / 'assets/examples/alarm_unit_test.json')
            save(source, original)

    def test_invalid_spec_not_published(self):
        source = self.job / 'source/unit-test-spec.json'
        data = load(source)
        del data['cases'][0]['steps'][0]['expected']['return_code']
        save(source, data)
        try:
            result = self.run_cli('render', '--run', 'invalid')
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((self.job / 'renders/invalid').exists())
            self.assertIn('required', result.stderr)
        finally:
            save(source, load(SKILL / 'assets/examples/alarm_unit_test.json'))

    def test_input_change_rejected(self):
        source = self.job / 'inputs/AlarmQualification.c'
        original = source.read_bytes()
        source.write_bytes(original + b'\n')
        try:
            result = self.run_cli('validate')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('hash mismatch', result.stderr)
        finally:
            source.write_bytes(original)

    def test_legacy_pass_rejected(self):
        path = self.job / 'records/execution-record.json'
        original = path.read_bytes()
        data = load(path)
        data['results'][0]['status'] = 'passed'
        data['results'][0]['evidence'] = ['old aggregate log']
        save(path, data)
        try:
            result = self.run_cli('validate')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('cannot import pass', result.stderr)
        finally:
            path.write_bytes(original)

    def test_existing_job_rejected(self):
        result = cli(SKILL, 'new-job', '--code-job', CODE_JOB,
                     '--workspace', self.root, '--job', 'sample')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already exists', result.stderr)


if __name__ == '__main__':
    unittest.main()
