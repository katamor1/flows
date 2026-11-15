import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
SKILL = PACKAGE / 'skills/routine-unit-test-spec'
spec = importlib.util.spec_from_file_location('ut_contract', SKILL / 'scripts/_contract.py')
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)
WORKSPACE = PACKAGE.parents[1]


class BootstrapTests(unittest.TestCase):
    def test_missing_required_fields_rejected(self):
        schema = {'type': 'object', 'properties': {'document': {'type': 'object'}},
                  'required': ['document'], 'additionalProperties': False}
        with self.assertRaises(ValueError):
            contract.validate({}, schema, {})


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample = json.loads((SKILL / 'assets/examples/alarm_unit_test.json').read_text(encoding='utf-8'))
        cls.schema = json.loads((SKILL / 'assets/schema/unit-test-spec.schema.json').read_text(encoding='utf-8'))
        cls.program = json.loads((WORKSPACE / 'prototypes/routine-code-poc/input/spec.json').read_text(encoding='utf-8'))

    def validate(self, data):
        return contract.validate(data, self.schema, self.program)

    def test_valid_specification(self):
        self.assertEqual(self.validate(copy.deepcopy(self.sample)), self.sample)

    def test_duplicate_case(self):
        data = copy.deepcopy(self.sample)
        data['cases'].append(copy.deepcopy(data['cases'][0]))
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_missing_expected_value(self):
        data = copy.deepcopy(self.sample)
        del data['cases'][0]['steps'][0]['expected']['return_code']
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_unknown_spec_reference(self):
        data = copy.deepcopy(self.sample)
        data['cases'][0]['spec_refs'] = ['P-DOES-NOT-EXIST']
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_wrong_family_cardinality(self):
        data = copy.deepcopy(self.sample)
        data['families'][0]['combination_count'] += 1
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_wrong_sequence_call_count(self):
        data = copy.deepcopy(self.sample)
        data['families'][-1]['call_count'] -= 1
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_changed_input_hash(self):
        data = copy.deepcopy(self.sample)
        data['target']['source_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_pass_result_in_spec_rejected(self):
        data = copy.deepcopy(self.sample)
        data['cases'][0]['status'] = 'passed'
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_legacy_pass_in_execution_rejected(self):
        record = contract.execution_record(self.sample)
        record['results'][0]['status'] = 'passed'
        record['results'][0]['evidence'] = ['legacy_aggregate']
        with self.assertRaises(ValueError):
            contract.validate_execution(record, self.sample)

    def test_initial_execution_is_not_executed(self):
        record = contract.execution_record(self.sample)
        contract.validate_execution(record, self.sample)
        expected = sum(len(self.sample[k]) for k in ('cases', 'families', 'static_checks'))
        self.assertEqual(len(record['results']), expected)
        self.assertTrue(all(x['status'] == 'not_executed' for x in record['results']))

    def test_dangling_coverage_item(self):
        data = copy.deepcopy(self.sample)
        data['coverage'][0]['item_ids'].append('UT-MISSING')
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_duplicate_step_id(self):
        data = copy.deepcopy(self.sample)
        data['cases'][0]['steps'].append(copy.deepcopy(data['cases'][0]['steps'][0]))
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_unknown_instance(self):
        data = copy.deepcopy(self.sample)
        data['cases'][0]['steps'][0]['instance'] = 'MISSING'
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_no_eval_token(self):
        data = copy.deepcopy(self.sample)
        data['cases'][0]['steps'][0]['signal_on'] = '__import__("os").system("echo bad")'
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_schema_unknown_keyword_fails_closed(self):
        schema = copy.deepcopy(self.schema)
        schema['anyOf'] = []
        with self.assertRaises(ValueError):
            contract.validate(copy.deepcopy(self.sample), schema, self.program)

    def test_empty_caller_assignment_has_visible_placeholder(self):
        sys.path.insert(0, str(SKILL / 'scripts'))
        import _renderer
        view = _renderer.context(self.sample, SKILL / 'assets/examples/alarm_unit_test.json')['view']
        empty_refs = {r['spec_ref'] for r in self.sample['coverage'] if not r['item_ids']}
        self.assertTrue(empty_refs)
        for row in view['coverage']:
            if row['ref'] in empty_refs:
                self.assertEqual(row['items'], '対象ケースなし（別工程）')


if __name__ == '__main__':
    unittest.main()
