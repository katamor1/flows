import copy
import json
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest
SKILL = Path(__file__).resolve().parents[1] / 'skills/routine-unit-test-spec'
sys.path.insert(0, str(SKILL / 'scripts'))
import _contract as contract

def fixture():
    program = {'document': {'id': 'Any specification', 'routine_id': 'range', 'routine_name': 'RangeClamp', 'status': 'draft'},
               'trial_assumptions': [], 'open_issues': [], 'interface': {'preconditions': 'lower <= upper'},
               'behavior': {'steps': [{'id': 'preserve', 'text': 'Inclusive clamp'}]}, 'constraints': [], 'verification_examples': []}
    target = {key: 'a' * 64 for key in ('program_spec_sha256', 'source_sha256', 'header_sha256')}
    data = {'schema_version': '0.2.0',
            'document': {'id': 'UT any name', 'title': 'Clamp test', 'revision': '1', 'date': '2026-11-17',
                         'status': 'draft', 'status_label': 'Draft', 'routine_id': 'range', 'routine_name': 'RangeClamp',
                         'template_id': 'unit-test-spec-v02', 'author': 'Codex'},
            'target': copy.deepcopy(target), 'summary': 'Derived from the input specification.', 'environment': [], 'assumptions': [],
            'cases': [{'id': 'ordinary', 'title': 'Within bounds', 'purpose': 'Preserve value', 'spec_refs': ['preserve'],
                       'initial_conditions': [], 'steps': [{'id': 'call', 'action': 'Call RangeClamp',
                          'inputs': [{'name': 'value', 'value': 2}],
                          'expected': [{'target': 'return', 'comparison': 'equals', 'value': 2}], 'repeat': 1, 'note': ''}],
                       'judgment': 'Return equals 2'}],
            'families': [], 'static_checks': [],
            'coverage': [{'spec_ref': 'preserve', 'method': 'test', 'item_ids': ['ordinary'], 'rationale': 'Ordinary clamp'},
                         {'spec_ref': '/interface/preconditions', 'method': 'caller', 'item_ids': [], 'rationale': 'Caller supplies ordered bounds'}],
            'open_issues': []}
    return data, program, target

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.data, self.program, self.target = fixture()
        self.schema = json.loads((SKILL / 'assets/schema/unit-test-spec.schema.json').read_text(encoding='utf-8'))
    def validate(self): return contract.validate(self.data, self.schema, self.program, self.target)
    def test_arbitrary_ids_empty_lists_and_native_values(self):
        self.validate()
        for value in [None, True, False, 4.25, -103, 'INT_MIN', {'x': [1, None, True]}, '__import__("os")']:
            self.data['cases'][0]['steps'][0]['inputs'][0]['value'] = value
            self.validate()
    def test_empty_step_inputs_and_arbitrary_comparison(self):
        self.data['cases'][0]['steps'][0]['inputs'] = []
        self.data['cases'][0]['steps'][0]['expected'][0].update(comparison='within_tolerance', value={'reference': 2.5, 'tolerance': 0.01})
        self.validate()
    def test_source_hash_must_match_actual_inputs(self):
        self.data['target']['source_sha256'] = '0' * 64
        with self.assertRaises(ValueError): self.validate()
    def test_duplicate_unknown_and_unmapped_items_rejected(self):
        for mutation in ('duplicate', 'unknown', 'unmapped', 'missing_coverage'):
            with self.subTest(mutation=mutation):
                self.setUp()
                if mutation == 'duplicate': self.data['cases'].append(copy.deepcopy(self.data['cases'][0]))
                if mutation == 'unknown': self.data['cases'][0]['spec_refs'] = ['unknown']
                if mutation == 'unmapped': self.data['coverage'][0]['item_ids'] = []
                if mutation == 'missing_coverage': self.data['coverage'].pop()
                with self.assertRaises(ValueError): self.validate()
    def test_families_compute_general_product_and_sequence(self):
        base = {'id': 'arbitrary-family', 'title': 'Finite family', 'spec_refs': ['preserve'], 'mode': 'product',
                'dimensions': [{'name': 'sample', 'values': [None, {'x': 1}, [2]]}, {'name': 'mode', 'values': [False, True]}],
                'sequence_length': 0, 'combination_count': 6, 'calls_per_instance': 2, 'call_count': 12,
                'initial': 'Independent values', 'enumeration': 'Written order', 'method': 'Compare all calls',
                'expected_rule': 'From input specification', 'examples': []}
        self.data['families'] = [base]
        self.data['coverage'][0]['item_ids'].append(base['id'])
        self.validate()
        base.update(mode='sequence', dimensions=[{'name': 'alphabet', 'values': ['read', 'hold']}], sequence_length=3,
                    combination_count=8, calls_per_instance=5, call_count=40)
        self.validate()
        base['call_count'] = 24
        with self.assertRaises(ValueError): self.validate()
    def test_nonfinite_empty_expected_and_unknown_keywords_rejected(self):
        self.data['cases'][0]['steps'][0]['inputs'][0]['value'] = float('nan')
        with self.assertRaises(ValueError): self.validate()
        self.setUp()
        self.data['cases'][0]['steps'][0]['expected'] = []
        with self.assertRaises(ValueError): self.validate()
        self.setUp()
        self.schema['properties']['families']['items']['anyOf'] = []
        with self.assertRaises(ValueError): self.validate()
    def test_empty_work_and_legacy_pass_rejected(self):
        self.data['cases'] = []
        with self.assertRaises(ValueError): self.validate()
        self.setUp()
        record = contract.execution_record(self.data)
        contract.validate_execution(record, self.data)
        record['results'][0]['status'] = 'passed'
        record['results'][0]['evidence'] = ['old log']
        with self.assertRaises(ValueError): contract.validate_execution(record, self.data)
    def test_payload_id_keys_are_not_source_declarations(self):
        program = json.loads((SKILL / 'assets/examples/range-clamp/program-spec.json').read_text(encoding='utf-8'))
        data = json.loads((SKILL / 'assets/examples/range-clamp/unit-test-spec.json').read_text(encoding='utf-8'))
        program['behavior']['configuration'] = [
            {'name': 'active', 'value': {'id': 'payload-id', 'nested': [{'id': 'CLAMP-STEP-LOWER'}]}, 'meaning': 'Active JSON payload'},
            {'name': 'fallback', 'value': {'id': 'payload-id'}, 'meaning': 'Fallback JSON payload'}]
        # Decision result fields also carry arbitrary JSON, including a literal id.
        for row in program['behavior']['decision_rows'][:2]: row['id'] = 'payload-id'
        workspace = SKILL.parents[3]
        stage_one = workspace / 'packages/routine-spec-officecli/skills/routine-spec-doc'
        module_spec = importlib.util.spec_from_file_location('program_spec_contract', stage_one / 'scripts/_contract.py')
        upstream = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(upstream)
        upstream.validate(program, json.loads((stage_one / 'assets/schema/routine-spec.schema.json').read_text(encoding='utf-8')))
        target = copy.deepcopy(data['target'])
        target['program_spec_sha256'] = hashlib.sha256(json.dumps(program, ensure_ascii=False).encode('utf-8')).hexdigest()
        data['target'] = copy.deepcopy(target)
        # Required declaration coverage uses pointers for arbitrary payload records.
        for n in range(2):
            data['coverage'].append({'spec_ref': '/behavior/configuration/'+str(n), 'method': 'unverified', 'item_ids': [], 'rationale': 'Payload configuration has no test evidence.'})
        data['coverage'].append({'spec_ref': '/behavior/configuration/0/value/id', 'method': 'unverified', 'item_ids': [], 'rationale': 'Literal nested payload remains addressable by JSON Pointer.'})
        contract.validate(data, self.schema, program, target)
        self.assertNotIn('payload-id', contract.collect_ids(program))
        self.assertEqual(contract.collect_ids(program).count('CLAMP-STEP-LOWER'), 1)
        self.assertNotIn('payload-id', contract.required_refs(program))
        self.assertIn('/behavior/decision_rows/0', contract.required_refs(program))
        # Genuine duplicate declaration IDs are still rejected.
        program['behavior']['steps'][1]['id'] = program['behavior']['steps'][0]['id']
        with self.assertRaisesRegex(ValueError, 'Duplicate source specification IDs'):
            contract.validate(data, self.schema, program, target)

    def test_empty_view_is_display_only(self):
        import _renderer
        original = copy.deepcopy(self.data)
        view = _renderer.context(self.data, SKILL / 'assets/schema/unit-test-spec.schema.json')['view']
        self.assertTrue(view['families'])
        self.assertTrue(view['assumptions'])
        self.assertEqual(original, self.data)

if __name__ == '__main__': unittest.main()
