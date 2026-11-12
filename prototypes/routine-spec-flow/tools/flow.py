"""Small JSON -> tagged DOCX prototype. No control-program implementation."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"\{\{([a-zA-Z0-9_.]+)\}\}")
VERSION = "0.1.0"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve(data, path):
    value = data
    for part in path.split("."):
        value = value[part]
    return value


def schema_from_example(value):
    """Freeze this prototype's object shape; not a universal schema generator."""
    if isinstance(value, dict):
        return {"type": "object", "properties": {k: schema_from_example(v) for k, v in value.items()},
                "required": list(value), "additionalProperties": False}
    if isinstance(value, list):
        assert value, "Empty array requires an explicit schema"
        return {"type": "array", "minItems": 1, "items": schema_from_example(value[0])}
    if type(value) is int:
        return {"type": "integer", "minimum": 1}
    if isinstance(value, str):
        return {"type": "string", "minLength": 1}
    raise ValueError(f"Unsupported sample value {value!r}")


def validate_value(value, schema, path="$", errors=None):
    """Validate only the explicitly supported keywords used by our schema.

    The JSON Schema file remains interoperable with a full Draft 2020-12 validator.
    Unknown validation keywords fail closed instead of being silently ignored.
    """
    if errors is None:
        errors = []
    supported = {"$schema", "$id", "title", "description", "type", "properties", "required",
                 "additionalProperties", "items", "minItems", "minLength", "minimum", "const"}
    unknown = set(schema) - supported
    if unknown:
        errors.append(f"{path}: unsupported schema keywords {sorted(unknown)}")
        return errors
    types = {"object": dict, "array": list, "string": str, "integer": int}
    expected = schema.get("type")
    if expected and type(value) is not types[expected]:
        errors.append(f"{path}: expected {expected}")
        return errors
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                errors.append(f"{path}.{k}: required")
        for k, v in value.items():
            if k in schema.get("properties", {}):
                validate_value(v, schema["properties"][k], path + "." + k, errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}.{k}: unknown field")
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: too few items")
        for i, v in enumerate(value):
            validate_value(v, schema["items"], f"{path}[{i}]", errors)
    elif isinstance(value, str) and len(value) < schema.get("minLength", 0):
        errors.append(f"{path}: empty string")
    elif type(value) is int and value < schema.get("minimum", value):
        errors.append(f"{path}: below minimum")
    return errors


def validate(data, schema):
    errors = validate_value(data, schema)
    if errors:
        raise ValueError("\n".join(errors))
    if data["document"]["status"] != "draft_trial":
        raise ValueError("This prototype cannot create approved specifications")
    if data["behavior"]["threshold"] != 10:
        raise ValueError("This sample's rules and examples are defined for threshold 10")
    for path in ("trial_assumptions", "behavior.steps", "constraints", "verification_examples", "open_issues"):
        ids = [r["id"] for r in resolve(data, path)]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate IDs in {path}")
    return data


def canonical_zip(path):
    """Remove ZIP timestamp variation so identical inputs produce identical bytes."""
    with ZipFile(path) as z:
        members = {n: z.read(n) for n in z.namelist()}
    temporary = Path(str(path) + ".tmp")
    with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(members):
            info = ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            z.writestr(info, members[name])
    temporary.replace(path)


def font(run, size=None, bold=None):
    run.font.name = "Yu Gothic"
    run.font.color.rgb = RGBColor(0, 0, 0)
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for item in ("ascii", "hAnsi", "eastAsia", "cs"):
        rf.set(qn("w:" + item), "Yu Gothic")
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold


def para(doc, text, style=None, size=None):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.05
    snap = OxmlElement("w:snapToGrid")
    snap.set(qn("w:val"), "0")
    p._p.get_or_add_pPr().append(snap)
    font(p.add_run(text), size)
    return p


def heading(doc, text):
    p = para(doc, text, "Heading 1", 11.5)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    if text.startswith(("4 ", "6 ", "9 ")):
        p.paragraph_format.page_break_before = True
    return p


def table(doc, headers, keys, widths, collection=None, rows=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    pr = t._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        for k, v in (("val", "single"), ("sz", "4"), ("color", "D9D9D9")):
            el.set(qn("w:" + k), v)
        borders.append(el)
    pr.append(borders)
    margins = OxmlElement("w:tblCellMar")
    for edge in ("top", "bottom", "left", "right"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:w"), "70" if edge in ("top", "bottom") else "90")
        el.set(qn("w:type"), "dxa")
        margins.append(el)
    pr.append(margins)
    if collection:
        caption = OxmlElement("w:tblCaption")
        caption.set(qn("w:val"), "repeat:" + collection)
        pr.append(caption)
    repeat = OxmlElement("w:tblHeader")
    t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for i, (cell, label, width) in enumerate(zip(t.rows[0].cells, headers, widths)):
        cell.text = label
        cell.width = Mm(width)
        shade = OxmlElement("w:shd")
        shade.set(qn("w:fill"), "E8EEF4")
        cell._tc.get_or_add_tcPr().append(shade)
    records = rows if rows is not None else [["{{" + k + "}}" for k in keys]]
    for record in records:
        cells = t.add_row().cells
        for cell, value, width in zip(cells, record, widths):
            cell.text = value
            cell.width = Mm(width)
    for row_index, row in enumerate(t.rows):
        no_split = OxmlElement("w:cantSplit")
        row._tr.get_or_add_trPr().append(no_split)
        for i, cell in enumerate(row.cells):
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.line_spacing = 1.0
                snap = OxmlElement("w:snapToGrid")
                snap.set(qn("w:val"), "0")
                p._p.get_or_add_pPr().append(snap)
                if widths[i] <= 18:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for r in p.runs:
                    font(r, 8.8, row_index == 0)
    spacer = para(doc, "", size=2)
    spacer.paragraph_format.space_before = Pt(0)
    spacer.paragraph_format.space_after = Pt(0)
    spacer.paragraph_format.line_spacing = Pt(3)
    return t


def make_template(destination):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.top_margin, sec.bottom_margin = Mm(17), Mm(16)
    sec.left_margin, sec.right_margin = Mm(18), Mm(18)
    sec.header_distance, sec.footer_distance = Mm(7), Mm(7)
    for grid in list(sec._sectPr.findall(qn("w:docGrid"))):
        sec._sectPr.remove(grid)
    for border in list(doc.styles.element.iter(qn("w:pBdr"))):
        border.getparent().remove(border)
    normal_ppr = doc.styles["Normal"]._element.get_or_add_pPr()
    snap = OxmlElement("w:snapToGrid")
    snap.set(qn("w:val"), "0")
    normal_ppr.append(snap)
    for name in ("Normal", "Title", "Heading 1", "Heading 2"):
        st = doc.styles[name]
        st.font.name = "Yu Gothic"
        st.font.color.rgb = RGBColor(0, 0, 0)
        st.font.size = Pt(9.5)
        st._element.get_or_add_rPr().append(OxmlElement("w:rFonts"))
        st._element.rPr.rFonts.set(qn("w:eastAsia"), "Yu Gothic")
    doc.styles["Title"].font.size = Pt(17)
    h = sec.header.paragraphs[0]
    font(h.add_run("{{document.routine_id}}   {{document.status_label}}"), 8)
    foot = sec.footer.paragraphs[0]
    foot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    font(foot.add_run("{{document.id}}  Rev {{document.revision}}  正本 {{build.source_short_hash}}   "), 7.5)
    for index, field_name in enumerate(("PAGE", "NUMPAGES")):
        if index:
            slash_run = OxmlElement("w:r")
            slash_text = OxmlElement("w:t")
            slash_text.set(qn("xml:space"), "preserve")
            slash_text.text = " / "
            slash_run.append(slash_text)
            foot._p.append(slash_run)
        field = OxmlElement("w:fldSimple")
        field.set(qn("w:instr"), field_name)
        run = OxmlElement("w:r")
        text = OxmlElement("w:t")
        text.text = "1"
        run.append(text)
        field.append(run)
        foot._p.append(field)
    doc.core_properties.title = "ルーチン仕様書テンプレート"
    doc.core_properties.author = ""
    doc.core_properties.created = datetime(2026, 11, 13, tzinfo=timezone.utc)
    doc.core_properties.modified = datetime(2026, 11, 13, tzinfo=timezone.utc)

    para(doc, "{{document.title}}", "Title", 17)
    para(doc, "{{document.status_label}}  |  {{document.date}}", size=9)
    table(doc, ["管理項目", "値"], [], [32, 142], rows=[
        ["文書IDと版", "{{document.id}}  Rev {{document.revision}}"],
        ["ルーチン", "{{document.routine_id}}  {{document.routine_name}}"],
        ["対象と責任", "{{interface.language}}  {{interface.visibility}}"],
    ])
    heading(doc, "1 目的と適用範囲")
    para(doc, "{{overview.purpose}}")
    para(doc, "{{overview.scope}}")
    heading(doc, "2 試作用の前提")
    table(doc, ["ID", "前提"], ["id", "text"], [17, 157], "trial_assumptions")
    heading(doc, "3 呼出しインターフェース")
    para(doc, "{{interface.prototype}}", size=8.8)
    table(doc, ["引数", "方向", "型と契約"], ["name", "direction", "type_contract"], [27, 15, 132], "view.parameters")

    heading(doc, "4 型と状態")
    para(doc, "{{interface.type_definitions}}", size=8.8)
    table(doc, ["状態", "初期値", "範囲と意味"], ["name", "initial", "range_meaning"], [41, 15, 118], "view.state_fields")
    table(doc, ["結果項目", "意味"], ["name", "meaning"], [36, 138], "behavior.result_fields")
    heading(doc, "5 判定手順と条件表")
    table(doc, ["手順", "処理"], ["id", "text"], [17, 157], "behavior.steps")
    table(doc, ["条件", "旧値", "新値", "成立", "新規"], ["condition", "old_count", "new_count", "qualified", "event"], [43, 37, 42, 26, 26], "behavior.decision_rows")
    para(doc, "{{behavior.postconditions}}", size=9)
    heading(doc, "6 戻り値と呼出し前提")
    table(doc, ["戻り値", "意味"], ["value", "meaning"], [18, 156], "interface.return_codes")
    para(doc, "{{interface.preconditions}}", size=9)

    heading(doc, "7 実行と資源の制約")
    table(doc, ["ID", "分類", "制約"], ["id", "category", "text"], [20, 25, 129], "constraints")
    para(doc, "{{behavior.timing_semantics}}", size=9)
    heading(doc, "8 仕様確認用の入出力例")
    table(doc, ["ID", "入力と操作", "期待する結果"], ["id", "input", "expected"], [21, 65, 88], "verification_examples")
    heading(doc, "9 要求との対応")
    para(doc, "{{overview.requirement_id}}  {{overview.source_locator}}", size=8.5)
    para(doc, "{{overview.source_requirement}}", size=8.5)
    table(doc, ["要求", "担当仕様", "確認先"], ["requirement", "specification", "verification"], [55, 70, 49], "traceability")
    heading(doc, "10 確認と決定が必要な事項")
    table(doc, ["ID", "担当", "決定事項"], ["id", "owner", "decision"], [17, 30, 127], "open_issues")
    destination.parent.mkdir(parents=True, exist_ok=True)
    doc.save(destination)
    canonical_zip(destination)


def replace_paragraph(p, context, used):
    original = p.text
    if not TOKEN.search(original):
        return
    def substitution(match):
        path = match.group(1)
        value = resolve(context, path)
        if not isinstance(value, (str, int)):
            raise ValueError(f"Scalar token points to a non-scalar value: {path}")
        used.add(path)
        return str(value)
    if all(any(match.group(0) in r.text for r in p.runs) for match in TOKEN.finditer(original)):
        for run in p.runs:
            if TOKEN.search(run.text):
                run.text = TOKEN.sub(substitution, run.text)
        return
    if p._p.findall('.//' + qn('w:fldChar')) or p._p.findall('.//' + qn('w:fldSimple')):
        raise ValueError('Split token in paragraph containing Word fields; keep each token in one run')
    replaced = TOKEN.sub(substitution, original)
    first = p.runs[0] if p.runs else p.add_run()
    first.text = replaced
    for run in p.runs[1:]:
        run.text = ""


def fill_table(t, context, used):
    cap = t._tbl.tblPr.find(qn("w:tblCaption"))
    if cap is not None and cap.get(qn("w:val"), "").startswith("repeat:"):
        path = cap.get(qn("w:val"))[7:]
        rows = resolve(context, path)
        if len(t.rows) != 2:
            raise ValueError(f"Repeat table {path} must contain a header and one prototype row")
        prototype = t.rows[1]._tr
        for i, row in enumerate(rows):
            clone = copy.deepcopy(prototype)
            t._tbl.insert(t._tbl.index(prototype) + i, clone)
            from docx.table import _Row
            for cell in _Row(clone, t).cells:
                for p in cell.paragraphs:
                    replace_paragraph(p, row, used)
        t._tbl.remove(prototype)
    else:
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    replace_paragraph(p, context, used)


def build(source, schema, template, output, manifest):
    data = validate(load(source), load(schema))
    context = copy.deepcopy(data)
    context["build"] = {"source_short_hash": sha(source)[:12]}
    context["view"] = {
        "parameters": [{**p, "type_contract": p["type"] + "\n" + p["contract"]} for p in data["interface"]["parameters"]],
        "state_fields": [{**p, "range_meaning": p["range"] + " " + p["meaning"]} for p in data["behavior"]["state_fields"]],
    }
    doc = Document(template)
    used = set()
    for p in doc.paragraphs:
        replace_paragraph(p, context, used)
    for t in doc.tables:
        fill_table(t, context, used)
    for section in doc.sections:
        for container in (section.header, section.footer):
            for p in container.paragraphs:
                replace_paragraph(p, context, used)
    doc.core_properties.title = data["document"]["title"]
    doc.core_properties.subject = data["document"]["routine_id"]
    doc.core_properties.author = data["document"]["author"]
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    canonical_zip(output)
    with ZipFile(output) as z:
        for name in z.namelist():
            if name.startswith("word/") and name.endswith(".xml"):
                if b"{{" in z.read(name) or b"}}" in z.read(name):
                    raise ValueError(f"Unresolved template token in {name}")
    record = {"generator_version": VERSION, "source": source.relative_to(ROOT).as_posix() if source.is_relative_to(ROOT) else source.name,
              "source_sha256": sha(source), "schema_sha256": sha(schema), "template_sha256": sha(template),
              "output": output.name, "output_sha256": sha(output), "status": data["document"]["status"],
              "repeat_tables": len(doc.tables), "tokens_used": sorted(used)}
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init-schema", "template", "validate", "build"])
    parser.add_argument("--source", type=Path, default=ROOT / "source/alarm_qualification.json")
    parser.add_argument("--schema", type=Path, default=ROOT / "schema/routine-spec.schema.json")
    parser.add_argument("--template", type=Path, default=ROOT / "templates/routine-spec-v01.docx")
    parser.add_argument("--output", type=Path, default=ROOT / "output/PS-RTN-ALM-001.docx")
    parser.add_argument("--manifest", type=Path, default=ROOT / "output/manifest.json")
    args = parser.parse_args()
    if args.command == "init-schema":
        s = schema_from_example(load(args.source))
        s = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Routine specification prototype 0.1", **s}
        s["properties"]["document"]["properties"]["status"]["const"] = "draft_trial"
        s["properties"]["schema_version"]["const"] = "0.1.0"
        args.schema.parent.mkdir(parents=True, exist_ok=True)
        args.schema.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Schema initialized; review and version this file before further data changes")
    elif args.command == "template":
        make_template(args.template)
        print("Template created: " + str(args.template))
    elif args.command == "validate":
        validate(load(args.source), load(args.schema))
        print("PASS: schema subset and prototype semantics")
    else:
        print(json.dumps(build(args.source, args.schema, args.template, args.output, args.manifest), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
