"""Maintainer-only schema build; runtime uses the sealed generated schema."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / 'skills/routine-unit-test-spec'
def s(const=None, empty=False):
    result = {'type': 'string', 'minLength': 0 if empty else 1}
    if const is not None: result['const'] = const
    return result
def i(minimum=0): return {'type': 'integer', 'minimum': minimum}
def a(item, minimum=0): return {'type': 'array', 'items': item, 'minItems': minimum}
def o(**fields): return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}
value = {}
named = o(name=s(), value=value)
step = o(id=s(), action=s(), inputs=a(named), expected=a(o(target=s(), comparison=s(), value=value), 1), repeat=i(1), note=s(empty=True))
case = o(id=s(), title=s(), purpose=s(), spec_refs=a(s(), 1), initial_conditions=a(named), steps=a(step, 1), judgment=s())
family = o(id=s(), title=s(), spec_refs=a(s(), 1), mode={'type': 'string', 'enum': ['product', 'sequence']},
           dimensions=a(o(name=s(), values=a(value, 1)), 1), sequence_length=i(), combination_count=i(1), calls_per_instance=i(1),
           call_count=i(1), initial=s(), enumeration=s(), method=s(), expected_rule=s(), examples=a(s()))
static = o(id=s(), title=s(), spec_refs=a(s(), 1), method=s(), criterion=s(), boundary=s())
schema = o(schema_version=s('0.2.0'),
           document=o(id=s(), title=s(), revision=s(), date=s(), status=s(), status_label=s(), routine_id=s(), routine_name=s(),
                      template_id=s('unit-test-spec-v02'), author=s()),
           target=o(program_spec_sha256=s(), source_sha256=s(), header_sha256=s()), summary=s(), environment=a(s()),
           assumptions=a(o(id=s(), text=s())), cases=a(case), families=a(family), static_checks=a(static),
           coverage=a(o(spec_ref=s(), method={'type': 'string', 'enum': ['test', 'review', 'test_and_review', 'caller', 'out_of_scope', 'unverified']},
                        item_ids=a(s()), rationale=s())), open_issues=a(o(id=s(), owner=s(), decision=s())))
schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:routine-unit-test-officecli:schema:0.2.0',
          'title': 'Generic finite JSON unit-test specification', **schema}
path = ROOT / 'assets/schema/unit-test-spec.schema.json'
path.write_text(json.dumps(schema, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(path)
