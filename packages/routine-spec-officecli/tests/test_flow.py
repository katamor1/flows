"""Integration checks using the actual Bob-bundled OfficeCLI and Python -S."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/routine-spec-doc'
EXE = Path(os.environ.get('SPEC_OFFICECLI_TEST_EXE',
    'C:/Users/stell/AppData/Local/Programs/IBM Bob/resources/app/extensions/bob-code/dist/officecli.exe'))
REFERENCE = ROOT.parents[1] / 'prototypes/routine-spec-flow/output/PS-RTN-ALM-001.docx'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def paragraphs(node):
    def text(p):
        return ''.join((e.text or '') if e.tag == W+'t' else '\n' if e.tag == W+'br'
                       else '\t' if e.tag == W+'tab' else '' for e in p.iter())
    return [text(p) for p in node.iter(W+'p')]


def contents(path):
    with ZipFile(path) as z:
        return {name: paragraphs(ET.fromstring(z.read(name))) for name in z.namelist()
                if name == 'word/document.xml' or name.startswith(('word/header', 'word/footer')) and name.endswith('.xml')}


class OfficeCliFlowTests(unittest.TestCase):
    def setUp(self):
        base = Path(os.environ.get('SPEC_OFFICECLI_TEST_TEMP', str(ROOT / 'qa/test-temp')))
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.base = Path(self.temp.name)
        self.skill = self.base / 'project/.bob/skills/routine-spec-doc'
        if SKILL.exists():
            shutil.copytree(SKILL, self.skill)
        self.workspace = self.base / 'project/仕様 jobs'

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, command, *extra, ok=True, exe=EXE):
        # -S is intentional: site-packages, python-docx and lxml are unavailable.
        p = subprocess.run([sys.executable, '-S', '-B', str(self.skill / 'scripts/specflow.py'),
             command, '--officecli', str(exe), *map(str, extra)], capture_output=True,
             text=True, encoding='utf-8', env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
            return json.loads(p.stdout)
        self.assertNotEqual(p.returncode, 0, p.stdout)
        return p

    def args(self):
        return ['--workspace', self.workspace, '--job', 'alarm-01']

    def new(self, fixture='assets/examples/alarm_qualification.json'):
        self.cli('new-job', *self.args(), '--spec', self.skill/fixture)
        return self.workspace / 'alarm-01/source/spec.json'

    def change(self, source, mutate):
        data = json.loads(source.read_text(encoding='utf-8'))
        mutate(data)
        source.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    def render(self, run='r001'):
        result = self.cli('render', *self.args(), '--run', run)
        path = Path(result['document'])
        return path, json.loads((path.parent/'manifest.json').read_text(encoding='utf-8'))

    def test_legacy_alarm_end_to_end_without_site_packages(self):
        doctor = self.cli('doctor')
        self.assertEqual(doctor['renderer']['version'], '1.0.144')
        source = self.new()
        self.cli('validate', *self.args())
        path, manifest = self.render()
        text='\n'.join(contents(path)['word/document.xml'])
        self.assertIn('old_count = 0から10',text)
        self.assertIn('threshold = 10',text)
        data=json.loads(source.read_text(encoding='utf-8'))
        for step in data['behavior']['steps']:
            self.assertIn(step['text'],text)
        self.assertEqual(manifest['generator_backend'], 'officecli')
        self.assertEqual(manifest['source_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertTrue(json.loads((path.parent/'officecli-validation.json').read_text(encoding='utf-8'))['success'])
        receipt = json.loads((path.parent/'officecli-batch.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['data']['summary']['failed'], 0)
        self.assertEqual(manifest['content_check']['status'], 'passed')

    def test_literal_token_text_xml_symbols_newlines_and_backslashes(self):
        source = self.new()
        value = '日本語 & <tag> "引用" $1 {{id}} {{document.title}}\n次行\tTAB \\n \\path'
        self.change(source, lambda d: d['trial_assumptions'][0].update(text=value))
        path, _ = self.render()
        self.assertIn(value, contents(path)['word/document.xml'])

    def test_dynamic_rows_and_repeatable_content(self):
        source = self.new()
        self.change(source, lambda d: d['trial_assumptions'].extend([
            {'id': 'ASM-X1', 'text': '追加された前提1'}, {'id': 'ASM-X2', 'text': '追加された前提2'}]))
        first, one = self.render()
        second, two = self.render('r002')
        self.assertEqual(contents(first), contents(second))
        self.assertEqual(one['semantic_sha256'], two['semantic_sha256'])
        self.assertIn('追加された前提2', contents(first)['word/document.xml'])

    def test_existing_job_and_run_are_not_overwritten(self):
        source = self.new()
        original = source.read_bytes()
        self.cli('new-job', *self.args(), ok=False)
        self.assertEqual(source.read_bytes(), original)
        path, _ = self.render()
        original = path.read_bytes()
        self.cli('render', *self.args(), '--run', 'r001', ok=False)
        self.assertEqual(path.read_bytes(), original)

    def test_unsupported_input_and_control_characters_do_not_publish(self):
        source = self.new()
        original = source.read_bytes()
        self.change(source, lambda d: d['behavior']['decision_rows'][0].pop('condition'))
        self.cli('render', *self.args(), '--run', 'r001', ok=False)
        self.assertFalse((source.parents[1]/'renders/r001').exists())
        source.write_bytes(original)
        self.change(source, lambda d: d['overview'].update(purpose='bad\x01data'))
        self.cli('render', *self.args(), '--run', 'r001', ok=False)
        self.assertFalse((source.parents[1]/'renders/r001').exists())

    def test_missing_renderer_modified_asset_and_path_escape_refused(self):
        self.cli('doctor', exe=self.base/'missing.exe', ok=False)
        self.cli('new-job', '--workspace', self.workspace, '--job', '../escape', ok=False)
        self.cli('new-job', '--workspace', self.skill/'jobs', '--job', 'alarm', ok=False)
        template = self.skill/'assets/templates/routine-spec-v02.docx'
        template.write_bytes(template.read_bytes()+b'changed')
        self.cli('doctor', ok=False)
        self.assertFalse(self.workspace.exists())

    def test_job_renderer_lock_mismatch_refused(self):
        source = self.new()
        lock = source.parents[1]/'package-lock.json'
        record = json.loads(lock.read_text(encoding='utf-8'))
        record['renderer']['sha256'] = '0'*64
        lock.write_text(json.dumps(record), encoding='utf-8')
        self.cli('render', *self.args(), '--run', 'r001', ok=False)
        self.assertFalse((source.parents[1]/'renders/r001').exists())

    def test_every_docx_mutation_is_an_officecli_command(self):
        self.new()
        path, manifest = self.render()
        plan = json.loads((path.parent/'officecli-commands.json').read_text(encoding='utf-8'))
        self.assertTrue(any(op['command'] == 'add' and 'from' in op for op in plan))
        self.assertTrue(any(op['command'] == 'set' and 'find' in op.get('props', {}) for op in plan))
        self.assertEqual(manifest['officecli']['sha256'], hashlib.sha256(EXE.read_bytes()).hexdigest())
        for script in (self.skill/'scripts').glob('*.py'):
            text = script.read_text(encoding='utf-8')
            self.assertNotIn('from docx', text)
            self.assertNotIn('import lxml', text)
            self.assertNotIn('writestr(', text)

    def test_page_fields_are_reported_and_preserved(self):
        self.new()
        path, manifest = self.render()
        fields = []
        with ZipFile(path) as archive:
            for name in archive.namelist():
                if name.startswith('word/') and name.endswith('.xml'):
                    fields.extend(node.get(W+'instr', '').strip() for node in ET.fromstring(archive.read(name)).iter(W+'fldSimple'))
        self.assertIn('PAGE', fields)
        self.assertIn('NUMPAGES', fields)
        reported = json.dumps(manifest['content_check']['field_codes'])
        self.assertIn('NUMPAGES', reported)

    def test_zero_match_successful_officecli_command_is_rejected(self):
        sys.path.insert(0, str(self.skill/'scripts'))
        try:
            spec = importlib.util.spec_from_file_location('test_renderer', self.skill/'scripts/_renderer.py')
            renderer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(renderer)
            target = self.base/'zero-match.docx'
            shutil.copyfile(self.skill/'assets/templates/routine-spec-v01.docx', target)
            commands = [{'command':'set', 'path':'/body', 'props':{'find':'__NOT_PRESENT_A__', 'replace':'x'}},
                        {'command':'set', 'path':'/body', 'props':{'find':'__NOT_PRESENT_B__', 'replace':'y'}}]
            plan = self.base/'zero-match.json'
            plan.write_text(json.dumps(commands), encoding='utf-8')
            reply = renderer.full_batch_reply(renderer.execute_json(EXE, ['batch', target, '--input', plan, '--json']))
            self.assertTrue(reply['success'])
            with self.assertRaisesRegex(ValueError, 'Unexpected replacement count'):
                renderer.verify_receipt(reply, commands, {'clones':0, 'replacements':[{'path':'/body','token':'absent','count':1}]})
        finally:
            sys.path.pop(0)

    def test_page_geometry_and_header_links_are_part_of_content_contract(self):
        sys.path.insert(0, str(self.skill/'scripts'))
        try:
            spec = importlib.util.spec_from_file_location('test_section_renderer', self.skill/'scripts/_renderer.py')
            renderer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(renderer)
            parts = renderer.document_parts(self.skill/'assets/templates/routine-spec-v01.docx')
            original = renderer.semantic_model(parts)
            section = parts['word/document.xml'].find(W+'body/'+W+'sectPr')
            section.find(W+'pgSz').set(W+'w', '12000')
            changed = renderer.semantic_model(parts)
            self.assertTrue(original != changed, 'Page geometry changes were silently ignored')
        finally:
            sys.path.pop(0)

    def test_styles_changed_by_officecli_are_detected(self):
        sys.path.insert(0, str(self.skill/'scripts'))
        try:
            spec = importlib.util.spec_from_file_location('test_static_renderer', self.skill/'scripts/_renderer.py')
            renderer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(renderer)
            template = self.skill/'assets/templates/routine-spec-v01.docx'
            target = self.base/'changed-style.docx'
            shutil.copyfile(template, target)
            renderer.execute_json(EXE, ['set', target, '/styles/Normal', '--prop', 'font=Arial', '--json'])
            renderer.execute_json(EXE, ['close', target, '--json'])
            self.assertTrue(renderer.unmodified_parts(template) != renderer.unmodified_parts(target),
                            'A style change was ignored')
        finally:
            sys.path.pop(0)

    def test_transient_windows_publish_denial_can_retry_without_overwrite(self):
        spec = importlib.util.spec_from_file_location('test_publish_flow', self.skill/'scripts/specflow.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        stage = self.base/'stage'
        stage.mkdir()
        (stage/'data.txt').write_text('kept', encoding='utf-8')
        destination = self.base/'published'
        rename = Path.rename
        calls = []
        def sometimes_denied(path, target):
            calls.append(1)
            if len(calls) == 1:
                error = PermissionError('Transient Windows sharing denial')
                error.winerror = 5
                raise error
            return rename(path, target)
        with patch.object(Path, 'rename', sometimes_denied):
            module.publish_stage(stage, destination)
        self.assertEqual((destination/'data.txt').read_text(encoding='utf-8'), 'kept')
        self.assertEqual(len(calls), 2)

    def test_range_clamp_empty_collections_no_threshold_and_byte_identity(self):
        fixture='assets/examples/range-clamp/spec.json'
        source=self.new(fixture)
        self.assertEqual(source.read_bytes(),(self.skill/fixture).read_bytes())
        before=source.read_bytes()
        self.cli('validate',*self.args())
        path,manifest=self.render()
        text='\n'.join(contents(path)['word/document.xml'])
        self.assertIn('int RangeClamp(int value, int lower, int upper);',text)
        self.assertIn('return = lower',text)
        self.assertIn('該当なし',text)
        self.assertNotIn('old_count',text)
        self.assertNotIn('threshold =',text)
        self.assertEqual(source.read_bytes(),before)
        self.assertEqual((source.parents[1]/'.gitattributes').read_bytes(),b'* -text\n')
        self.assertEqual(manifest['status'],'draft_trial')

    def test_generic_configuration_decision_json_and_no_fixed_counts(self):
        source=self.new('assets/examples/range-clamp/spec.json')
        def mutate(d):
            d['document'].update(id='PS-SYNTHETIC-X9',routine_id='LIB-Z',routine_name='ReadLatest',status='review_pending',status_label='Review pending')
            d['interface']['prototype']='void ReadLatest(void);'
            d['interface']['parameters']=[]
            d['interface']['return_codes']=[]
            d['behavior']['threshold']=-2.75
            d['behavior']['configuration']=[{'name':'mode','value':{'channels':['east',3,None,True]},'meaning':'Select channels without evaluation.'},{'name':'literal','value':'{{document.id}}','meaning':'Literal input tag.'}]
            d['behavior']['decision_rows']=[{'condition':'available','next.sample':{'value':4,'valid':True},'return':None,'flags':[1,2]}]
            d['trial_assumptions']=[{'id':'AX.3','text':'An arbitrary assumption ID.'}]
            d['behavior']['state_fields']=[{'name':'cache.sample','type':'long','initial':'-4','range':'any long','meaning':'The current stored sample.'}]
            d['verification_examples']=[]
            d['traceability']=[]
            d['constraints']=[]
        self.change(source,mutate)
        snapshot=source.read_bytes()
        path,manifest=self.render()
        self.assertEqual(path.name,'PS-SYNTHETIC-X9.docx')
        self.assertEqual(manifest['status'],'review_pending')
        text='\n'.join(contents(path)['word/document.xml'])
        for expected in ('void ReadLatest(void);','threshold = -2.75','mode = {"channels":["east",3,null,true]}','literal = {{document.id}}','cache.sample\nlong','next.sample = {"value":4,"valid":true}','return = null','flags = [1,2]','AX.3'):
            self.assertIn(expected,text)
        self.assertEqual(source.read_bytes(),snapshot)

    def test_blank_skeleton_minimum_and_identity_options_do_not_inject_rules(self):
        self.cli('new-job',*self.args(),'--routine-name','ReadValue','--routine-id','COMP-42','--document-id','PS-COMP-42')
        source=self.workspace/'alarm-01/source/spec.json'
        data=json.loads(source.read_text(encoding='utf-8'))
        self.assertEqual(data['document']['routine_name'],'ReadValue')
        self.assertEqual(data['behavior']['decision_rows'],[])
        self.assertNotIn('threshold',data['behavior'])
        self.assertNotIn('Alarm',source.read_text(encoding='utf-8'))
        self.cli('validate',*self.args(),ok=False)
        self.cli('render',*self.args(),'--run','never',ok=False)
        self.assertFalse((source.parents[1]/'renders/never').exists())
        self.cli('new-job','--workspace',self.workspace,'--job','minimum')
        self.cli('validate','--workspace',self.workspace,'--job','minimum',ok=False)

    def test_bad_json_unknown_fields_duplicates_nonfinite_and_missing_condition(self):
        source=self.new('assets/examples/range-clamp/spec.json')
        original=source.read_bytes()
        def duplicate(d): d['behavior']['steps'].append(d['behavior']['steps'][0].copy())
        mutations=[lambda d:d.update(unexpected=True),duplicate,
                   lambda d:d['behavior']['decision_rows'][0].pop('condition'),
                   lambda d:d['behavior'].update(configuration=[{'name':'bad','value':float('nan'),'meaning':'bad'}]),
                   lambda d:d['behavior']['decision_rows'][0].update({'bad\x01key':1})]
        for mutate in mutations:
            source.write_bytes(original)
            self.change(source,mutate)
            self.cli('render',*self.args(),'--run','bad',ok=False)
            self.assertFalse((source.parents[1]/'renders/bad').exists())

    def test_job_guard_and_payload_guard_are_required(self):
        source=self.new()
        (source.parents[1]/'.gitattributes').write_bytes(b'* text\n')
        self.cli('validate',*self.args(),ok=False)
        (self.skill/'.gitattributes').unlink()
        self.cli('doctor',ok=False)

    def test_unknown_schema_keywords_rejected_even_without_rows(self):
        sys.path.insert(0,str(self.skill/'scripts'))
        try:
            spec=importlib.util.spec_from_file_location('test_generic_contract',self.skill/'scripts/_contract.py')
            contract=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(contract)
            with self.assertRaisesRegex(ValueError,'unsupported schema keywords'):
                contract.validate_value([],{'type':'array','items':{'type':'object','oneOf':[]}})
        finally:
            sys.path.pop(0)

    def test_no_argument_function_with_all_collections_empty(self):
        source=self.new('assets/examples/range-clamp/spec.json')
        def mutate(d):
            d['document'].update(id='PS-NOARGS-9',routine_id='NOARGS',routine_name='Pulse')
            d['overview'].update(purpose='Synthetic no-argument presentation fixture.',scope='Document renderer acceptance only.',coverage='No business behavior is asserted.')
            d['interface'].update(prototype='void Pulse(void);',parameters=[],return_codes=[],type_definitions='',preconditions='No arguments or caller-owned storage.')
            d['behavior'].update(state_fields=[],result_fields=[],steps=[],decision_rows=[],configuration=[],postconditions='Presentation fixture only.',timing_semantics='No runtime timing is asserted.')
            for name in ('trial_assumptions','constraints','verification_examples','traceability','open_issues'): d[name]=[]
        self.change(source,mutate)
        path,_=self.render()
        text='\n'.join(contents(path)['word/document.xml'])
        self.assertIn('void Pulse(void);',text)
        self.assertGreaterEqual(text.count('該当なし'),12)

    def test_supplied_sample_hold_state_configuration_and_status(self):
        self.new('assets/examples/sample-hold/spec.json')
        path,manifest=self.render()
        text='\n'.join(contents(path)['word/document.xml'])
        for expected in ('SampleHold_Update','Project_ReadSample','ProjectMock_Reset','state.last_sample\nint','state.has_sample\nint','API calls = 0','return = -2','SH-STEP-COMMIT'):
            self.assertIn(expected,text)
        self.assertEqual(manifest['status'],'fixture_only')


if __name__ == '__main__':
    unittest.main(verbosity=2)
