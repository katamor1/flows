"""Maintainer-only schema build. The runtime ships the resulting fixed JSON."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills/routine-unit-test-spec"


def s(const=None):
    result = {"type": "string", "minLength": 1}
    if const is not None:
        result["const"] = const
    return result


def i(minimum=None):
    result = {"type": "integer"}
    if minimum is not None:
        result["minimum"] = minimum
    return result


def a(item, minimum=1):
    return {"type": "array", "items": item, "minItems": minimum}


def o(**fields):
    return {"type": "object", "properties": fields, "required": list(fields),
            "additionalProperties": False}


expected = o(return_code=i(), state_count=s(), out_count=s(), qualified=s(),
             became_qualified=s(), preservation=s())
step = o(id=s(), instance=s(), state_pointer=s(), result_pointer=s(),
         signal_on=s(), sample_valid=s(), repeat=i(1), expected=expected, note=s())
initial = o(instance=s(), state_count=s(), state_fill_byte=s("0xA5"),
            result_fill_byte=s("0x5A"),
            result=o(qualified=s(), became_qualified=s(), on_count=s()))
case = o(id=s(), title=s(), purpose=s(), spec_refs=a(s()), initial=a(initial),
         steps=a(step), judgment=s())
family = o(id=s(), title=s(), spec_refs=a(s()), mode=s(),
           dimensions=a(o(name=s(), values=a(s()))), sequence_length=i(0),
           combination_count=i(1), call_count=i(1), initial=s(), enumeration=s(),
           method=s(), expected_rule=s(), examples=a(s()))
static = o(id=s(), title=s(), spec_refs=a(s()), method=s(), criterion=s(), boundary=s())
schema = o(
    schema_version=s("0.1.0"),
    document=o(id=s("UTS-RTN-ALM-001"), title=s(), revision=s(), date=s(),
               status=s("draft_trial"), status_label=s("試作仕様 要件確認前"),
               routine_id=s("RTN-ALM-001"), routine_name=s("AlarmQualification_Update"),
               template_id=s("unit-test-spec-v01"), author=s()),
    target=o(program_spec_sha256=s(), source_sha256=s(), header_sha256=s()),
    summary=s(), environment=a(s()), assumptions=a(o(id=s(), text=s())),
    cases=a(case, 16), families=a(family, 4), static_checks=a(static),
    coverage=a(o(spec_ref=s(), method=s(), item_ids=a(s(), 0), rationale=s())),
    open_issues=a(o(id=s(), owner=s(), decision=s()))
)
schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
          "$id": "urn:routine-unit-test-officecli:schema:0.1.0",
          "title": "C90 alarm unit-test specification trial profile", **schema}
path = ROOT / "assets/schema/unit-test-spec.schema.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(path)
