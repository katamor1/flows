"""Generic framework acceptance tests, independent of generated routine bodies.

fixture-implementations contains known scaffolding, excluded from the skill.
The former sample-fixed tests are preserved in legacy-v01-workflow.py.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
SKILL = PACKAGE / 'skills/routine-code-c90'
WORKSPACE = PACKAGE.parents[1]
EXAMPLES = SKILL / 'assets/examples'
FIXTURES = PACKAGE / 'tests/fixture-implementations'
CLANG = Path(os.environ.get('SKILL_GENERIC_CLANG', 'C:/Program Files/LLVM/bin/clang.exe'))


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cli(*args):
    return subprocess.run(
        [sys.executable, '-X', 'utf8', '-S', '-B', str(SKILL / 'scripts/codegen.py'), *map(str, args)],
        capture_output=True, text=True, encoding='utf-8', timeout=180)


class WorkflowCase(unittest.TestCase):
    def setUp(self):
        parent = WORKSPACE / 'artifacts/routine-code-skill/generic-tests'
        parent.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='case-', dir=parent)).resolve()

    def expect_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def expect_error(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn('Package resource changed', result.stderr)
        self.assertNotIn('Package inventory mismatch', result.stderr)
        self.assertNotIn('Package release version mismatch', result.stderr)
        return result.stderr + result.stdout

    def prepare(self, example='range-clamp', job='case', profile=True, spec=None, profile_path=None):
        spec = spec or EXAMPLES / example / 'spec.json'
        args = ['prepare', '--spec', spec, '--workspace', self.root, '--job', job]
        if profile:
            args += ['--verification-profile', profile_path or EXAMPLES / example / 'verification-profile.json']
        self.expect_ok(cli(*args))
        return self.root / job

    def materialize(self, job):
        config = read_json(job / 'job.json')
        shutil.copyfile(FIXTURES / (config['routine_name'] + '.c'), job / config['source'])
        (job / 'traceability.md').write_text(
            'Framework-only known fixture: ' + config['routine_name'] + '.\n'
            'Acceptance expected values were authored separately from this body.\n', encoding='utf-8')

    def record(self, job='case', generation='g001'):
        return cli('record', '--workspace', self.root, '--job', job, '--generation', generation,
                   '--agent', 'Codex-framework-test', '--agent-version', 'stdlib-unittest',
                   '--bob-executed', 'no', '--note', 'Known C fixture to test framework only; no model quality claim.')

    def verify(self, job='case', run='r001'):
        return cli('verify', '--workspace', self.root, '--job', job, '--clang', CLANG, '--run', run)

    def prepared_source(self, example='range-clamp', profile=True, job='case', profile_path=None):
        path = self.prepare(example, job=job, profile=profile, profile_path=profile_path)
        self.materialize(path)
        self.expect_ok(self.record(job=job))
        return path

    def custom_profile(self, example='range-clamp', **updates):
        source = EXAMPLES / example / 'verification-profile.json'
        profile = read_json(source)
        profile['headers'] = [dict(item, source=str((source.parent / item['source']).resolve()))
                              for item in profile['headers']]
        for field in ('test_sources', 'support_sources'):
            profile[field] = [str((source.parent / name).resolve()) for name in profile[field]]
        profile.update(updates)
        target = self.root / ('profile-' + str(len(list(self.root.glob('profile-*.json')))) + '.json')
        write_json(target, profile)
        return target


class PreparationTests(WorkflowCase):
    def test_stateless_empty_types_prepare_without_answer(self):
        job = self.prepare(profile=False)
        config = read_json(job / 'job.json')
        self.assertEqual(config['format_version'], '0.2.0')
        self.assertEqual(config['routine_name'], 'RangeClamp')
        self.assertEqual(config['routine_id'], 'RTN-CLAMP-001')
        self.assertEqual(config['header'], 'include/RangeClamp.h')
        self.assertEqual(config['source'], 'src/RangeClamp.c')
        self.assertEqual(config['tests'], [])
        self.assertFalse((job / config['source']).exists())
        self.assertFalse((job / 'records/pending.json').exists())
        self.assertIn('int RangeClamp(int value, int lower, int upper);',
                      (job / config['header']).read_text(encoding='ascii'))
        self.assertEqual((job / config['spec']).read_bytes(), (EXAMPLES / 'range-clamp/spec.json').read_bytes())

    def test_header_and_source_names_follow_different_routine(self):
        job = self.prepare('sample-hold')
        config = read_json(job / 'job.json')
        self.assertEqual(config['header'], 'include/SampleHold_Update.h')
        self.assertEqual(config['source'], 'src/SampleHold_Update.c')
        self.assertTrue((job / config['header']).exists())
        self.assertFalse((job / 'include/AlarmQualification.h').exists())
        self.assertFalse((job / 'src/AlarmQualification.c').exists())
        self.assertEqual(config['allowed_undefined_symbols'], ['Project_ReadSample'])
        self.assertIn('PROJECT_SAMPLE_FIXTURE=1', config['defines'])

    def test_profile_assets_are_copied_and_bound_to_spec(self):
        job = self.prepare('sample-hold')
        config = read_json(job / 'job.json')
        self.assertEqual(config['spec_sha256'], sha(EXAMPLES / 'sample-hold/spec.json'))
        self.assertEqual((job / config['profile']).read_bytes(),
                         (EXAMPLES / 'sample-hold/verification-profile.json').read_bytes())
        self.assertEqual(len(config['tests']), 1)
        self.assertEqual(len(config['support_sources']), 1)
        self.assertEqual((job / config['tests'][0]).read_bytes(),
                         (EXAMPLES / 'sample-hold/test_sample_hold.c').read_bytes())
        self.assertEqual((job / config['support_sources'][0]).read_bytes(),
                         (EXAMPLES / 'sample-hold/mock_project_sample.c').read_bytes())
        self.assertTrue((job / 'include/Project_Sample.h').exists())

    def test_extra_spec_fields_and_whitespace_are_preserved(self):
        value = read_json(EXAMPLES / 'range-clamp/spec.json')
        value['project_specific'] = {'note': 'retain this context', 'values': [4, 9]}
        different = self.root / 'project.json'
        different.write_text(json.dumps(value) + '\n\n', encoding='utf-8')
        job = self.prepare(profile=False, spec=different)
        self.assertEqual((job / read_json(job / 'job.json')['spec']).read_bytes(), different.read_bytes())

    def test_wrong_profile_routine_or_spec_hash_is_rejected(self):
        for target in ({'routine_name': 'OtherRoutine', 'spec_sha256': sha(EXAMPLES / 'range-clamp/spec.json')},
                       {'routine_name': 'RangeClamp', 'spec_sha256': '0' * 64}):
            with self.subTest(target=target):
                profile = self.custom_profile(target=target)
                self.expect_error(cli('prepare', '--spec', EXAMPLES / 'range-clamp/spec.json',
                                      '--verification-profile', profile, '--workspace', self.root, '--job', 'wrong'))
                self.assertFalse((self.root / 'wrong').exists())

    def test_name_prototype_mismatch_and_nonidentifier_are_rejected(self):
        for name in ('OtherRoutine', '../RangeClamp', '9RangeClamp'):
            with self.subTest(name=name):
                value = read_json(EXAMPLES / 'range-clamp/spec.json')
                value['document']['routine_name'] = name
                path = self.root / 'mismatch.json'
                write_json(path, value)
                self.expect_error(cli('prepare', '--spec', path, '--workspace', self.root, '--job', 'bad'))
                self.assertFalse((self.root / 'bad').exists())

    def test_target_name_only_inside_comment_is_not_a_declaration(self):
        value = read_json(EXAMPLES / 'range-clamp/spec.json')
        value['interface']['prototype'] = '/* int RangeClamp(int value); */ int Other(void);'
        spec = self.root / 'comment-only.json'
        write_json(spec, value)
        self.expect_error(cli('prepare', '--spec', spec, '--workspace', self.root, '--job', 'bad-comment'))
        self.assertFalse((self.root / 'bad-comment').exists())

    def test_profile_cannot_inject_header_paths_flags_or_commands(self):
        for change in ({'headers': [{'source': str(EXAMPLES / 'sample-hold/Project_Sample.h'), 'target': '../escape.h'}]},
                       {'defines': ['-include attacker.h']},
                       {'defines': ['ROUTINE_CODE_RANGECLAMP_H']},
                       {'command': ['python', '-c', 'print(1)']}):
            with self.subTest(change=change):
                profile = self.custom_profile(**change)
                self.expect_error(cli('prepare', '--spec', EXAMPLES / 'range-clamp/spec.json',
                                      '--verification-profile', profile, '--workspace', self.root, '--job', 'bad'))
                self.assertFalse((self.root / 'bad').exists())

    def test_duplicate_job_and_traversal_rejected_without_overwrite(self):
        job = self.prepare(profile=False)
        before = (job / 'job.json').read_bytes()
        self.expect_error(cli('prepare', '--spec', EXAMPLES / 'range-clamp/spec.json',
                              '--workspace', self.root, '--job', 'case'))
        self.assertEqual((job / 'job.json').read_bytes(), before)
        self.assertFalse((self.root / '.case.lock').exists())
        self.expect_error(cli('prepare', '--spec', EXAMPLES / 'range-clamp/spec.json',
                              '--workspace', self.root, '--job', '../escape'))

    def test_missing_mapping_and_wrong_source_filename_rejected(self):
        job = self.prepare(profile=False)
        (job / 'src/AlarmQualification.c').write_text('int wrong_name(void) { return 0; }\n', encoding='ascii')
        self.expect_error(self.record())
        self.materialize(job)
        (job / 'traceability.md').unlink()
        self.assertIn('traceability', self.expect_error(self.record()).lower())

    def test_fixed_input_header_test_support_profile_mutations_rejected(self):
        for kind in ('spec', 'header', 'tests', 'support_sources', 'profile'):
            with self.subTest(asset=kind):
                job_id = 'mutate-' + kind.replace('_', '-')
                job = self.prepare('sample-hold', job=job_id)
                self.materialize(job)
                config = read_json(job / 'job.json')
                relative = config[kind][0] if isinstance(config[kind], list) else config[kind]
                with (job / relative).open('ab') as output:
                    output.write(b'\n')
                self.expect_error(self.record(job=job_id))
                self.assertFalse((job / 'records/g001.json').exists())

    def test_duplicate_generation_cannot_overwrite(self):
        job = self.prepared_source(profile=False)
        before = (job / 'records/g001.json').read_bytes()
        self.expect_error(self.record())
        self.assertEqual((job / 'records/g001.json').read_bytes(), before)
        self.assertFalse((self.root / '.case.lock').exists())

    def test_existing_guard_refuses_record_verify_and_preserves_owner_lock(self):
        job = self.prepare(profile=False)
        self.materialize(job)
        guard = self.root / '.case.lock'
        guard.write_text('another operation owns this lock\n', encoding='ascii')
        self.expect_error(self.record())
        self.expect_error(self.verify())
        self.assertEqual(guard.read_text(encoding='ascii'), 'another operation owns this lock\n')


@unittest.skipUnless(CLANG.is_file(), 'Approved Clang required; set SKILL_GENERIC_CLANG to run real host checks')
class HostVerificationTests(WorkflowCase):
    def report(self, job, run='r001'):
        return read_json(job / 'qa' / run / 'verification.json')

    def assert_snapshot_compiled(self, job, report):
        config = read_json(job / 'job.json')
        snapshot = job / 'qa/r001/snapshot'
        self.assertEqual(report['snapshot_files'][config['source']], sha(job / config['source']))
        compiled = [item for item in report['commands'] if '-c' in item['argv']
                    and Path(item['argv'][item['argv'].index('-c') + 1]).name == Path(config['source']).name]
        self.assertEqual(len(compiled), 2)
        for command in compiled:
            source = Path(command['argv'][command['argv'].index('-c') + 1])
            self.assertTrue(source.resolve().is_relative_to(snapshot.resolve()))

    def test_no_profile_is_compiled_only_without_test_pass_claim(self):
        job = self.prepared_source(profile=False)
        self.expect_ok(self.verify())
        report = self.report(job)
        self.assertEqual(report['status'], 'compiled_only')
        self.assertEqual(report['test_execution'], 'not_provided')
        self.assertIn('-O0', json.dumps(report))
        self.assertIn('-O2', json.dumps(report))
        self.assert_snapshot_compiled(job, report)

    def test_workspace_path_with_spaces_compiles_and_tracks_dependencies(self):
        self.root = self.root / 'workspace with spaces'
        self.root.mkdir()
        job = self.prepared_source(profile=False)
        self.expect_ok(self.verify())
        report = self.report(job)
        self.assertEqual(report['status'], 'compiled_only')
        self.assertIn('workspace with spaces', json.dumps(report))

    def test_missing_frozen_header_fails_with_report(self):
        job = self.prepared_source(profile=False)
        config = read_json(job / 'job.json')
        (job / config['header']).unlink()
        self.expect_error(self.verify())
        self.assertEqual(self.report(job)['status'], 'failed')
        self.assertEqual(self.report(job)['test_execution'], 'not_run')

    def test_profile_test_source_basename_can_contain_spaces_and_unicode(self):
        source = self.root / 'independent 日本語 cases.c'
        shutil.copyfile(EXAMPLES / 'range-clamp/test_range_clamp.c', source)
        profile = self.custom_profile(test_sources=[str(source)])
        job = self.prepared_source(profile_path=profile)
        self.expect_ok(self.verify())
        report = self.report(job)
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['test_execution'], 'passed')
        self.assertIn('independent 日本語 cases.c', json.dumps(report, ensure_ascii=False))

    def test_nested_parameter_declaration_does_not_satisfy_global_interface(self):
        value = read_json(EXAMPLES / 'range-clamp/spec.json')
        value['interface']['prototype'] = 'int Other(int RangeClamp(void));'
        spec = self.root / 'nested-prototype.json'
        write_json(spec, value)
        job = self.prepare(profile=False, spec=spec)
        config = read_json(job / 'job.json')
        (job / config['source']).write_text('long RangeClamp(long value) { return value; }\n', encoding='ascii')
        (job / 'traceability.md').write_text('Negative fixture: target is only a parameter declaration.\n', encoding='ascii')
        self.expect_ok(self.record())
        self.expect_error(self.verify())
        self.assertEqual(self.report(job)['status'], 'failed')

    def test_range_clamp_cases_execute_at_both_optimizations(self):
        job = self.prepared_source()
        self.expect_ok(self.verify())
        self.assertEqual(self.report(job)['status'], 'passed')
        self.assertEqual(self.report(job)['test_execution'], 'passed')
        outputs = [p.read_text(encoding='utf-8') for p in (job / 'qa/r001').rglob('*.stdout.txt')]
        self.assertEqual(sum('RangeClamp: 15 literal cases passed' in text for text in outputs), 2)
        self.assertIn('-O0', json.dumps(self.report(job)))
        self.assertIn('-O2', json.dumps(self.report(job)))

    def test_state_and_allowed_synthetic_api_execute_with_support(self):
        job = self.prepared_source('sample-hold')
        self.expect_ok(self.verify())
        self.assertEqual(self.report(job)['status'], 'passed')
        outputs = [p.read_text(encoding='utf-8') for p in (job / 'qa/r001').rglob('*.stdout.txt')]
        self.assertEqual(sum('SampleHold_Update: literal state/API cases passed' in text for text in outputs), 2)
        self.assertIn('Project_ReadSample', json.dumps(self.report(job)))

    def test_unapproved_external_symbol_fails_with_report(self):
        profile = self.custom_profile('sample-hold', allowed_undefined_symbols=[])
        job = self.prepared_source('sample-hold', profile_path=profile)
        self.expect_error(self.verify())
        self.assertEqual(self.report(job)['status'], 'failed')
        self.assertIn('Project_ReadSample', json.dumps(self.report(job)))

    def test_wrong_body_fails_independent_acceptance_and_records_failure(self):
        job = self.prepare()
        config = read_json(job / 'job.json')
        (job / config['source']).write_text(
            '#include "RangeClamp.h"\nint RangeClamp(int value, int lower, int upper)\n'
            '{ (void)lower; (void)upper; return value; }\n', encoding='ascii')
        (job / 'traceability.md').write_text('Deliberately wrong fixture for negative acceptance.\n', encoding='ascii')
        self.expect_ok(self.record())
        self.expect_error(self.verify())
        self.assertEqual(self.report(job)['status'], 'failed')
        self.assertEqual(self.report(job)['test_execution'], 'failed')
        outputs = [p.read_text(encoding='utf-8') for p in (job / 'qa/r001').rglob('*.stdout.txt')]
        self.assertTrue(any('FAIL RangeClamp' in text for text in outputs))

    def test_source_edit_requires_new_generation_and_preserves_old_record(self):
        job = self.prepared_source(profile=False)
        config = read_json(job / 'job.json')
        before = (job / 'records/g001.json').read_bytes()
        with (job / config['source']).open('a', encoding='ascii') as output:
            output.write('\n/* reviewed edit requiring new generation */\n')
        self.expect_error(self.verify())
        self.assertEqual(self.report(job)['status'], 'failed')
        self.expect_ok(self.record(generation='g002'))
        self.expect_ok(self.verify(run='r002'))
        self.assertEqual(self.report(job, 'r002')['status'], 'compiled_only')
        self.assertEqual((job / 'records/g001.json').read_bytes(), before)
        self.assertNotEqual(read_json(job / 'records/g001.json')['source_sha256'],
                            read_json(job / 'records/g002.json')['source_sha256'])

    def test_post_record_input_header_test_support_mutations_fail(self):
        for kind in ('spec', 'header', 'tests', 'support_sources'):
            with self.subTest(asset=kind):
                job_id = 'post-' + kind.replace('_', '-')
                job = self.prepared_source('sample-hold', job=job_id)
                config = read_json(job / 'job.json')
                relative = config[kind][0] if isinstance(config[kind], list) else config[kind]
                with (job / relative).open('ab') as output:
                    output.write(b'\n')
                self.expect_error(self.verify(job=job_id))
                self.assertEqual(self.report(job)['status'], 'failed')

    def test_missing_test_file_fails_instead_of_becoming_passed(self):
        job = self.prepared_source()
        config = read_json(job / 'job.json')
        (job / config['tests'][0]).unlink()
        self.expect_error(self.verify())
        self.assertEqual(self.report(job)['status'], 'failed')
        self.assertEqual(self.report(job)['test_execution'], 'not_run')

    def test_duplicate_run_cannot_overwrite_evidence(self):
        job = self.prepared_source(profile=False)
        self.expect_ok(self.verify())
        before = (job / 'qa/r001/verification.json').read_bytes()
        self.expect_error(self.verify())
        self.assertEqual((job / 'qa/r001/verification.json').read_bytes(), before)
        self.assertFalse((self.root / '.case.lock').exists())

    def test_definition_incompatible_with_frozen_header_fails_without_include(self):
        job = self.prepare(profile=False)
        config = read_json(job / 'job.json')
        (job / config['source']).write_text(
            'long RangeClamp(int value, int lower, int upper)\n'
            '{ (void)lower; (void)upper; return value; }\n', encoding='ascii')
        (job / 'traceability.md').write_text('Negative fixture: incompatible return type.\n', encoding='ascii')
        self.expect_ok(self.record())
        self.expect_error(self.verify())
        self.assertEqual(self.report(job)['status'], 'failed')

    def test_profile_without_tests_is_still_only_compiled(self):
        profile = self.custom_profile(test_sources=[])
        job = self.prepared_source(profile_path=profile)
        self.expect_ok(self.verify())
        self.assertEqual(self.report(job)['status'], 'compiled_only')
        self.assertEqual(self.report(job)['test_execution'], 'not_provided')

    def test_legacy_alarm_explicit_profile_preserves_original_test_bytes(self):
        original = SKILL / 'assets/alarm-profile'
        job = self.prepare(spec=EXAMPLES / 'alarm-regression/spec.json',
                           profile_path=EXAMPLES / 'alarm-regression/verification-profile.json')
        config = read_json(job / 'job.json')
        self.assertEqual(config['header'], 'include/AlarmQualification_Update.h')
        self.assertEqual(config['source'], 'src/AlarmQualification_Update.c')
        self.assertEqual((job / config['tests'][0]).read_bytes(),
                         (original / 'tests/test_alarm_qualification.c').read_bytes())
        shutil.copyfile(WORKSPACE / 'prototypes/routine-code-poc/src/AlarmQualification.c', job / config['source'])
        (job / 'traceability.md').write_text('Legacy regression reuses independent acceptance tests.\n', encoding='ascii')
        self.expect_ok(self.record())
        self.expect_ok(self.verify())
        self.assertEqual(self.report(job)['status'], 'passed')


if __name__ == '__main__':
    unittest.main()
