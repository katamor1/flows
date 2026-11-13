"""Frozen runtime extracted from the routine-spec-flow prototype.
Only validation and rendering are shipped. No template/schema initializers.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from docx import Document
from docx.oxml.ns import qn
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
