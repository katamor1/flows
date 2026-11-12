"""Checks the document flow, not the unimplemented control routine."""
import copy
import json
import re
from pathlib import Path
from zipfile import ZipFile
from lxml import etree

from flow import ROOT, build, load, sha, validate

SOURCE = ROOT / "source/alarm_qualification.json"
SCHEMA = ROOT / "schema/routine-spec.schema.json"
TEMPLATE = ROOT / "templates/routine-spec-v01.docx"
DEST = ROOT / "qa/automated"


def text_of_docx(path):
    with ZipFile(path) as z:
        return "\n".join(" ".join(etree.fromstring(z.read(n)).itertext()) for n in z.namelist()
                         if n.startswith("word/") and n.endswith(".xml") and n not in ("word/styles.xml", "word/settings.xml"))


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    data, schema = load(SOURCE), load(SCHEMA)
    checks = []
    validate(data, schema)
    checks.append({"name": "valid_source", "status": "PASS"})
    variants = []
    changed = copy.deepcopy(data); del changed["document"]["id"]
    variants.append(("missing_required_field", changed))
    changed = copy.deepcopy(data); changed["unknown_field"] = "x"
    variants.append(("unknown_field", changed))
    changed = copy.deepcopy(data); changed["behavior"]["threshold"] = "10"
    variants.append(("wrong_type", changed))
    changed = copy.deepcopy(data); changed["document"]["status"] = "approved"
    variants.append(("self_approval_blocked", changed))
    changed = copy.deepcopy(data); changed["verification_examples"][1]["id"] = changed["verification_examples"][0]["id"]
    variants.append(("duplicate_ids", changed))
    for name, candidate in variants:
        try:
            validate(candidate, schema)
        except ValueError as e:
            checks.append({"name": name, "status": "PASS", "rejected_reason": str(e).splitlines()[0]})
        else:
            raise AssertionError("Invalid source accepted: " + name)
    outputs = []
    for i in (1, 2):
        out = DEST / f"rebuild-{i}.docx"
        build(SOURCE, SCHEMA, TEMPLATE, out, DEST / f"manifest-{i}.json")
        outputs.append(out)
    assert sha(outputs[0]) == sha(outputs[1]), "Non-reproducible output"
    assert sha(outputs[0]) == sha(ROOT / "output/PS-RTN-ALM-001.docx"), "Published output is stale or edited"
    checks.append({"name": "identical_inputs_identical_docx_bytes", "status": "PASS", "sha256": sha(outputs[0])})
    text = text_of_docx(outputs[0])
    compact = re.sub(r"\s+", "", text)
    assert "{{" not in text and "}}" not in text
    expected = [data["document"]["title"], data["interface"]["prototype"], data["interface"]["type_definitions"], data["overview"]["source_requirement"]]
    for collection in ("trial_assumptions", "constraints", "verification_examples", "open_issues"):
        for row in data[collection]:
            expected.extend(row.values())
    for value in expected:
        assert re.sub(r"\s+", "", str(value)) in compact, "Missing source content: " + str(value)
    checks.append({"name": "source_content_and_repeat_rows_preserved", "status": "PASS", "values_checked": len(expected)})
    changed = copy.deepcopy(data)
    changed["document"]["revision"] = "0.2-flow-check"
    changed_source = DEST / "changed-source.json"
    changed_source.write_text(json.dumps(changed, ensure_ascii=False, indent=2), encoding="utf-8")
    changed_doc = DEST / "changed-output.docx"
    build(changed_source, SCHEMA, TEMPLATE, changed_doc, DEST / "changed-manifest.json")
    assert "0.2-flow-check" in text_of_docx(changed_doc)
    assert sha(changed_doc) != sha(outputs[0])
    checks.append({"name": "source_revision_change_reaches_document", "status": "PASS"})
    with ZipFile(TEMPLATE) as z:
        assert b"{{" in z.read("word/document.xml")
        for name in ("word/styles.xml", "word/document.xml"):
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            assert not etree.fromstring(z.read(name)).xpath("//w:pBdr", namespaces=ns), "Unexpected paragraph border"
    checks.append({"name": "template_tokens_and_no_title_border", "status": "PASS"})
    with ZipFile(outputs[0]) as z:
        footer = etree.fromstring(z.read('word/footer1.xml'))
        instructions = footer.xpath('//w:fldSimple/@w:instr', namespaces=ns)
        assert [v.strip() for v in instructions] == ['PAGE', 'NUMPAGES'], 'Page fields were destroyed during substitution'
    checks.append({"name": "page_fields_preserved_after_substitution", "status": "PASS"})
    result = {"scope": "JSON-to-Word prototype verification; control C routine is not implemented or executed", "checks": checks,
              "passed": len(checks), "failed": 0, "source_sha256": sha(SOURCE), "template_sha256": sha(TEMPLATE),
              "output_sha256": sha(ROOT / "output/PS-RTN-ALM-001.docx")}
    (ROOT / "output/verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
