"""One-time maintainer repair of the fixed legacy Word template.

Python reads ZIP/XML, creates OfficeCLI instructions, and checks evidence.
Only OfficeCLI writes DOCX internals. No rendering or redesign is performed.
Run with --apply to copy the immutable source and execute the recorded batch.
All generated files (including OfficeCLI temporary/spill files) stay beside
this helper, in qa/template-repair.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
DEFAULT_SOURCE = WORKSPACE / "packages/routine-spec-kit/skills/routine-spec-doc/assets/templates/routine-spec-v01.docx"
DEFAULT_OFFICECLI = Path(r"C:\Users\stell\AppData\Local\Programs\IBM Bob\resources\app\extensions\bob-code\dist\officecli.exe")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
NS = {"w": W}
ET.register_namespace("w", W)

# Only these property containers require reordering in the legacy source.
# The order follows their OOXML schema sequences, without changing values.
ORDER = {
    "pPr": "pStyle keepNext keepLines pageBreakBefore framePr widowControl numPr suppressLineNumbers pBdr shd tabs suppressAutoHyphens kinsoku wordWrap overflowPunct topLinePunct autoSpaceDE autoSpaceDN bidi adjustRightInd snapToGrid spacing ind contextualSpacing mirrorIndents suppressOverlap jc textDirection textAlignment textboxTightWrap outlineLvl divId cnfStyle rPr sectPr pPrChange".split(),
    "tblPr": "tblStyle tblpPr tblOverlap bidiVisual tblStyleRowBandSize tblStyleColBandSize tblW jc tblCellSpacing tblInd tblBorders shd tblLayout tblCellMar tblLook tblCaption tblDescription tblPrChange".split(),
    "tblCellMar": "top left start bottom right end".split(),
}


def q(name: str) -> str:
    return "{" + W + "}" + name


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def dump_json(name: str, value: object) -> None:
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_package(path: Path) -> dict[str, bytes]:
    with ZipFile(path, mode="r") as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def walk_paths(root: ET.Element):
    def walk(node, xpath):
        yield node, xpath
        seen = Counter()
        for child in node:
            seen[child.tag] += 1
            prefix = "w:" if child.tag.startswith("{" + W + "}") else ""
            yield from walk(child, f"{xpath}/{prefix}{local(child.tag)}[{seen[child.tag]}]")
    yield from walk(root, f"/w:{local(root.tag)}[1]")


def reorder(node: ET.Element) -> bool:
    order = ORDER[local(node.tag)]
    ranks = {q(name): index for index, name in enumerate(order)}
    unknown = [child.tag for child in node if child.tag not in ranks]
    if unknown:
        raise ValueError(f"Unreviewed property child in {node.tag}: {unknown}")
    original = list(node)
    arranged = sorted(original, key=lambda child: ranks[child.tag])
    if original == arranged:
        return False
    node[:] = arranged
    return True


def make_plan(package: dict[str, bytes]):
    roots = {name: ET.fromstring(data) for name, data in package.items() if name.endswith(".xml")}
    for name in ("word/document.xml", "word/styles.xml", "word/settings.xml"):
        for node in roots[name].iter():
            if node.tag in {q("bidi"), q("rtl"), q("bidiVisual")} and node.get(q("val"), "1") not in {"0", "false", "off"}:
                raise ValueError("RTL template requires explicit review of indentation aliases")
    expected = {name: deepcopy(root) for name, root in roots.items()}
    commands, changes = [], []

    def replace(part, xpath, node, category, before):
        commands.append({"command": "raw-set", "part": part, "xpath": xpath, "action": "replace", "xml": ET.tostring(node, encoding="unicode")})
        changes.append({"part": part, "xpath": xpath, "category": category, "before": before, "after": [local(child.tag) for child in node]})

    document = expected["word/document.xml"]
    for node, xpath in walk_paths(document):
        if node.tag == q("pPr"):
            before = [local(child.tag) for child in node]
            if reorder(node):
                replace("/document", xpath, node, "paragraph_property_order", before)
        elif node.tag == q("tblPr"):
            before = [local(child.tag) for child in node]
            changed = reorder(node)
            for margins in node.findall("w:tblCellMar", NS):
                margin_before = [local(child.tag) for child in margins]
                if reorder(margins):
                    changed = True
                    changes.append({"part": "/document", "xpath": xpath + "/w:tblCellMar[1]", "category": "table_margin_order", "before": margin_before, "after": [local(child.tag) for child in margins]})
            if changed:
                replace("/document", xpath, node, "table_property_order", before)

    missing = []
    for node, xpath in walk_paths(document):
        if node.tag == q("shd") and q("val") not in node.attrib:
            missing.append(xpath)
            node.set(q("val"), "clear")
            changes.append({"part": "/document", "xpath": xpath, "category": "missing_shading_pattern", "added": {"w:val": "clear"}})
    if missing:
        commands.append({"command": "raw-set", "part": "/document", "xpath": "//w:shd[not(@w:val)]", "action": "setattr", "xml": "w:val=clear"})

    for node, xpath in walk_paths(expected["word/styles.xml"]):
        if node.tag != q("rPr"):
            continue
        fonts = node.findall("w:rFonts", NS)
        if len(fonts) <= 1:
            continue
        # The observed invalid source has a populated first rFonts and an
        # entirely empty duplicate at the end. Never merge competing values.
        if not fonts[0].attrib or any(font.attrib or len(font) or font.text for font in fonts[1:]):
            raise ValueError(f"Competing rFonts values require review: {xpath}")
        before = [local(child.tag) for child in node]
        for font in fonts[1:]:
            node.remove(font)
        replace("/styles", xpath, node, "empty_duplicate_rFonts", before)

    return roots, expected, commands, changes


def semantic(node: ET.Element):
    # OfficeCLI assigns paragraph identity metadata to a template that had none.
    # These IDs do not express text, field, table, layout, or formatting values.
    attrs = {key: value for key, value in node.attrib.items()
             if key not in {"{" + W14 + "}paraId", "{" + W14 + "}textId"}}
    # OpenXML SDK serializes legacy left/right indentation as start/end.
    # make_plan rejects an RTL template before this equivalence is used.
    if node.tag == q("ind"):
        for old, new in (("left", "start"), ("right", "end")):
            if q(old) in attrs and q(new) not in attrs:
                attrs[q(new)] = attrs.pop(q(old))
    # A tblLook bitmask and matching explicit flags carry the same values.
    if node.tag == q("tblLook") and q("val") in attrs:
        bits = int(attrs[q("val")], 16)
        for flag, mask in (("firstRow", 0x20), ("lastRow", 0x40), ("firstColumn", 0x80), ("lastColumn", 0x100), ("noHBand", 0x200), ("noVBand", 0x400)):
            value = attrs.get(q(flag))
            if value is not None and (value in {"1", "true", "on"}) == bool(bits & mask):
                attrs.pop(q(flag))
    text = node.text or ""
    if len(node) and not text.strip():
        text = ""  # XML indentation, never a leaf text value.
    tail = node.tail or ""
    if not tail.strip():
        tail = ""
    return node.tag, tuple(sorted(attrs.items())), text, tail, tuple(semantic(child) for child in node)


def content_evidence(package: dict[str, bytes]):
    roots = {name: ET.fromstring(data) for name, data in package.items() if name.startswith("word/") and name.endswith(".xml")}
    paragraphs = {name: ["".join(p.itertext()) for p in root.iter(q("p"))]
                  for name, root in roots.items() if name == "word/document.xml" or re.fullmatch(r"word/(header|footer)\d+\.xml", name)}
    tokens = {name: [token for text in texts for token in re.findall(r"\{\{[^{}]+\}\}", text)] for name, texts in paragraphs.items()}
    document = roots["word/document.xml"]
    tables = []
    for table in document.iter(q("tbl")):
        caption = table.find("w:tblPr/w:tblCaption", NS)
        tables.append({"caption": caption.get(q("val")) if caption is not None else None,
                       "cells_per_row": [len(row.findall("w:tc", NS)) for row in table.findall("w:tr", NS)]})
    fields = {name: [semantic(field) for field in root.iter(q("fldSimple"))] for name, root in roots.items() if next(root.iter(q("fldSimple")), None) is not None}
    return {"paragraph_text": paragraphs, "tokens": tokens, "tables": tables, "simple_fields": fields}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--officecli", type=Path, default=DEFAULT_OFFICECLI)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    officecli = args.officecli.resolve(strict=True)
    output = HERE / "routine-spec-v01-officecli.docx"
    if source == output:
        raise ValueError("Source must be immutable and distinct from output")
    before_hash = sha(source)
    original = read_package(source)
    roots, expected, commands, changes = make_plan(original)
    dump_json("repair-commands.json", commands)
    dump_json("repair-changes.json", changes)
    dump_json("repair-plan-summary.json", {"source": str(source), "source_sha256": before_hash, "officecli": str(officecli), "output": str(output), "commands": len(commands), "change_categories": dict(Counter(change["category"] for change in changes))})
    if not args.apply:
        print(json.dumps({"planned_commands": len(commands), "changes": dict(Counter(change["category"] for change in changes))}))
        return

    temporary = HERE / "tmp"
    temporary.mkdir(exist_ok=True)
    environment = os.environ.copy()
    environment.update({"TMP": str(temporary), "TEMP": str(temporary)})
    calls = []

    def run(label: str, arguments: list[str]):
        result = subprocess.run([str(officecli), *arguments], capture_output=True, encoding="utf-8-sig", env=environment, check=False)
        (HERE / (label + ".stdout.json")).write_text(result.stdout, encoding="utf-8")
        (HERE / (label + ".stderr.txt")).write_text(result.stderr, encoding="utf-8")
        calls.append({"label": label, "argv": [str(officecli), *arguments], "exit_code": result.returncode})
        dump_json("officecli-invocations.json", calls)
        return result.returncode, json.loads(result.stdout)

    _, baseline = run("validate-before", ["validate", str(source), "--json"])
    if baseline.get("success") is not False:
        raise AssertionError("Expected the legacy source validation to fail")
    shutil.copyfile(source, output)
    batch_code, batch = run("repair-batch", ["batch", str(output), "--input", str(HERE / "repair-commands.json"), "--stop-on-error", "--json"])
    data = batch.get("data", {})
    spill_path = None
    if "outputFile" in data:
        spill = Path(data["outputFile"]).resolve(strict=True)
        if not spill.is_relative_to(HERE):
            raise AssertionError(f"Unexpected spill destination outside QA: {spill}")
        data = json.loads(spill.read_text(encoding="utf-8-sig"))
        spill_path = str(spill)
    dump_json("repair-batch.full.json", data)
    if batch_code != 0 or batch.get("success") is not True:
        raise AssertionError("OfficeCLI repair batch failed; inspect its recorded results")
    results = data.get("results", [])
    if len(results) != len(commands) or any(item.get("success") is not True for item in results):
        raise AssertionError("Not all planned OfficeCLI commands succeeded")

    after_code, validation = run("validate-after", ["validate", str(output), "--json"])
    repaired = read_package(output)
    added_members = sorted(repaired.keys() - original.keys())
    removed_members = sorted(original.keys() - repaired.keys())
    if added_members != ["docProps/custom.xml"] or removed_members:
        raise AssertionError(f"Unexpected package member changes: {added_members}, {removed_members}")
    custom = ET.fromstring(repaired["docProps/custom.xml"])
    audit = {prop.get("name"): "".join(prop.itertext()) for prop in custom}
    if set(audit) != {"OfficeCLI.Version", "OfficeCLI.LastModified"} or audit["OfficeCLI.Version"] != "1.0.144" or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", audit["OfficeCLI.LastModified"]):
        raise AssertionError(f"Unexpected OfficeCLI custom properties: {audit}")
    mismatches, changed_parts, identity_counts = [], [], {}
    for name, original_bytes in original.items():
        if original_bytes != repaired[name]:
            changed_parts.append(name)
        if name.endswith(".xml") or name.endswith(".rels"):
            actual_root = ET.fromstring(repaired[name])
            expected_root = expected.get(name)
            if expected_root is None:
                expected_root = ET.fromstring(original_bytes)
            if name == "_rels/.rels":
                additions = [child for child in actual_root if child.get("Type", "").endswith("/custom-properties")]
                if len(additions) != 1 or additions[0].get("Target") not in {"docProps/custom.xml", "/docProps/custom.xml"}:
                    raise AssertionError("Unexpected custom-properties relationship")
                actual_root.remove(additions[0])
            elif name == "[Content_Types].xml":
                additions = [child for child in actual_root if child.get("PartName") == "/docProps/custom.xml"]
                if len(additions) != 1 or additions[0].get("ContentType") != "application/vnd.openxmlformats-officedocument.custom-properties+xml":
                    raise AssertionError("Unexpected custom-properties content type")
                actual_root.remove(additions[0])
            if semantic(actual_root) != semantic(expected_root):
                mismatches.append(name)
            ids = Counter(local(key) for node in actual_root.iter() for key in node.attrib if key in {"{" + W14 + "}paraId", "{" + W14 + "}textId"})
            if ids:
                identity_counts[name] = dict(ids)
        elif original_bytes != repaired[name]:
            mismatches.append(name)
    before_content = content_evidence(original)
    after_content = content_evidence(repaired)
    legacy_indents = sum(1 for node in roots["word/styles.xml"].iter(q("ind")) if q("left") in node.attrib or q("right") in node.attrib)
    table_look_count = len(list(roots["word/document.xml"].iter(q("tblLook"))))
    evidence = {"source_sha256_before": before_hash, "source_sha256_after": sha(source), "source_unchanged": before_hash == sha(source), "output_sha256": sha(output), "validation_success": after_code == 0 and validation.get("success") is True, "batch_summary": data.get("summary"), "batch_spill_file": spill_path, "change_categories": dict(Counter(change["category"] for change in changes)), "changed_package_members": changed_parts, "added_package_members": added_members, "unexpected_semantic_changes": mismatches, "matches_planned_repairs_and_documented_officecli_normalization": not mismatches, "paragraph_identity_metadata": identity_counts, "officecli_normalization": {"audit_custom_properties": audit, "legacy_indentation_alias_elements": legacy_indents, "indentation_alias_rule": "left/right -> start/end with identical values; active RTL rejected", "table_look_elements": table_look_count, "table_look_rule": "explicit flags removed only when exactly equal to the retained bitmask", "xml_indentation_whitespace": "ignored only outside leaf text values"}, "text_tokens_tables_and_fields_identical": before_content == after_content, "template_content": before_content, "rendering": "Not performed; root task will inspect appearance."}
    dump_json("repair-evidence.json", evidence)
    assert evidence["source_unchanged"], "Immutable source changed"
    assert evidence["validation_success"], "Repaired template still fails schema validation"
    assert not mismatches, f"Unexpected semantic changes: {mismatches}"
    assert evidence["text_tokens_tables_and_fields_identical"], "Template content changed"
    print(json.dumps({"output": str(output), "commands": len(commands), "validation_success": True, "unexpected_semantic_changes": mismatches, "source_unchanged": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
