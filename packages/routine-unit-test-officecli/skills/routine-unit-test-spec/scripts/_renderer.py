"""Generate DOCX exclusively through a pinned OfficeCLI executable.

Python reads XML to prepare commands and to verify the result. It never writes
DOCX/OOXML parts. The template and all document edits are owned by OfficeCLI.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from _contract import resolve

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
TOKEN = re.compile(r'\{\{([A-Za-z0-9_.]+)\}\}')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def document_parts(path):
    with ZipFile(path) as archive:
        return {name: ET.fromstring(archive.read(name)) for name in sorted(archive.namelist())
                if name == 'word/document.xml' or name.startswith(('word/header', 'word/footer')) and name.endswith('.xml')}


def ptext(paragraph):
    return ''.join((node.text or '') if node.tag == W+'t' else '\n' if node.tag == W+'br'
                   else '\t' if node.tag == W+'tab' else '' for node in paragraph.iter())


def text_values(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from text_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from text_values(item)
    elif isinstance(value, str):
        yield value


def check_xml_characters(data):
    for value in text_values(data):
        for char in value:
            n = ord(char)
            if not (n in (9, 10, 13) or 0x20 <= n <= 0xD7FF or 0xE000 <= n <= 0xFFFD or 0x10000 <= n <= 0x10FFFF):
                raise ValueError(f'Input contains an XML-incompatible character U+{n:04X}')


def context(data, source):
    """Generic scalar-only view. Empty sections get display rows, never canonical edits."""
    def refs(item): return '\n'.join(item['spec_refs'])
    def value(item): return json.dumps(item, ensure_ascii=False, sort_keys=True, allow_nan=False)
    def named(items): return '\n'.join(x['name']+' = '+value(x['value']) for x in items) or '該当なし'
    def rows(items, keys): return items or [{key: '該当なし' if n == 0 else '—' for n, key in enumerate(keys)}]
    case_index, case_steps = [], []
    for case in data['cases']:
        case_index.append({'id': case['id'], 'title': case['title'],
                           'purpose': '目的: '+case['purpose']+'\n判定基準: '+case['judgment'],
                           'refs': refs(case), 'status': '未実施'})
        for index, step in enumerate(case['steps']):
            inputs = []
            if index == 0: inputs.append('初期条件:\n'+named(case['initial_conditions']))
            inputs.append('操作: '+step['action']+'\n入力:\n'+named(step['inputs'])+'\nrepeat='+str(step['repeat']))
            expected = '\n'.join(x['target']+' ['+x['comparison']+'] '+value(x['value']) for x in step['expected'])
            case_steps.append({'case_step': case['id']+'/'+step['id'], 'inputs': '\n'.join(inputs),
                               'expected': expected+'\n注記: '+(step['note'] or '該当なし'), 'refs': refs(case)})
    families = []
    for family in data['families']:
        dimensions = '\n'.join(d['name']+' = '+value(d['values']) for d in family['dimensions'])
        families.append({'id': family['id'],
                         'definition': family['title']+f"\nmode={family['mode']}; sequence_length={family['sequence_length']}\n"
                         +dimensions+f"\ncombination_count={family['combination_count']}; calls_per_instance={family['calls_per_instance']}; call_count={family['call_count']}\n"
                         +'初期条件: '+family['initial']+'\n列挙順・展開ID: '+family['enumeration']
                         +'\n方法: '+family['method']+'\n具体例:\n'+('\n'.join(family['examples']) or '該当なし')+'\n実施状態: 未実施',
                         'oracle': family['expected_rule'], 'refs': refs(family)})
    doc = data['document']
    target_summary = '\n'.join(['schema_version='+data['schema_version'],
        f"文書: {doc['id']} / {doc['title']}", f"revision={doc['revision']}; date={doc['date']}; author={doc['author']}",
        f"status={doc['status']} / {doc['status_label']}; template_id={doc['template_id']}",
        f"対象: {doc['routine_id']} / {doc['routine_name']}"]
        +[key+':\n'+'\n'.join(v[i:i+32] for i in range(0, len(v), 32)) for key, v in data['target'].items()]
        +[f"代表ケース={len(data['cases'])}; 手順行={len(case_steps)}; 族={len(families)}; 静的確認={len(data['static_checks'])}",
          f"族内の組合せ/系列 合計={sum(f['combination_count'] for f in data['families'])}; 族内の呼出し照合 合計={sum(f['call_count'] for f in data['families'])}"])
    return {**data, 'build': {'source_short_hash': sha(source)[:12]}, 'view': {
        'target_summary': target_summary,
        'not_executed': '全ケース・族・静的確認は未実施。期待値は原仕様から定める。比較名と値は記述データであり、実行しない。要求承認・表示確認・C実行・RTOS検証は別記録で管理する。',
        'environment': rows([{'text': text} for text in data['environment']], ['text']),
        'assumptions': rows([dict(x) for x in data['assumptions']], ['id', 'text']),
        'case_index': rows(case_index, ['id', 'title', 'purpose', 'refs', 'status']),
        'case_steps': rows(case_steps, ['case_step', 'inputs', 'expected', 'refs']),
        'families': rows(families, ['id', 'definition', 'oracle', 'refs']),
        'static_checks': rows([{'id': x['id'], 'method': x['title']+'\n方法: '+x['method'],
                           'criterion': x['criterion']+'\n対象範囲・限界: '+x['boundary']+'\n実施状態: 未実施',
                           'refs': refs(x)} for x in data['static_checks']], ['id', 'method', 'criterion', 'refs']),
        'coverage': rows([{'ref': x['spec_ref'], 'method': x['method'], 'items': '\n'.join(x['item_ids']) or '対象ケースなし（別工程）',
                          'reason': x['rationale']} for x in data['coverage']], ['ref', 'method', 'items', 'reason']),
        'open_issues': rows([dict(x) for x in data['open_issues']], ['id', 'owner', 'decision'])}}


def scalar(value):
    if type(value) not in (str, int):
        raise ValueError('A template token must resolve to a string or integer')
    return str(value).replace('\r\n', '\n').replace('\r', '\n')


def render_text(text, values):
    return TOKEN.sub(lambda m: scalar(resolve(values, m.group(1))), text)


def caption(table):
    node = table.find(W+'tblPr/'+W+'tblCaption')
    return node.get(W+'val', '') if node is not None else ''


def properties(node):
    """Order-independent signature for formatting properties, not text content."""
    if node is None:
        return None
    return [node.tag, sorted(node.attrib.items()),
            sorted((properties(child) for child in node), key=lambda v: json.dumps(v, ensure_ascii=False))]


def paragraph_model(node, values):
    formats = {json.dumps(properties(run.find(W+'rPr')), sort_keys=True) for run in node.iter(W+'r')
               if any(t.text for t in run.iter(W+'t'))}
    text = ptext(node)
    return {'text': render_text(text, values) if values is not None else text,
            'pPr': properties(node.find(W+'pPr')), 'run_formats': sorted(formats)}


def row_model(row, values):
    return {'trPr': properties(row.find(W+'trPr')), 'cells': [
        {'tcPr': properties(cell.find(W+'tcPr')), 'paragraphs': [paragraph_model(p, values) for p in cell.findall(W+'p')]}
        for cell in row.findall(W+'tc')]}


def semantic_model(parts, values=None):
    model = {}
    for name, part in parts.items():
        root = part.find(W+'body') if name == 'word/document.xml' else part
        blocks = []
        for node in root:
            if node.tag == W+'p':
                blocks.append({'paragraph': paragraph_model(node, values)})
            elif node.tag == W+'tbl':
                rows = node.findall(W+'tr')
                cap = caption(node)
                if values is not None and cap.startswith('repeat:'):
                    if len(rows) != 2:
                        raise ValueError('Repeated tables must have one header and one prototype row')
                    rendered = [row_model(rows[0], values)] + [row_model(rows[1], row) for row in resolve(values, cap[7:])]
                else:
                    rendered = [row_model(row, values) for row in rows]
                blocks.append({'table': {'caption': cap, 'tblPr': properties(node.find(W+'tblPr')),
                                        'tblGrid': properties(node.find(W+'tblGrid')), 'rows': rendered}})
        model[name] = {'blocks': blocks,
                       'section_properties': [properties(n) for n in root.findall(W+'sectPr')],
                       'field_codes': [n.text or '' for n in part.iter(W+'instrText')]
                                      + [n.get(W+'instr', '') for n in part.iter(W+'fldSimple')],
                       'field_types': [n.get(W+'fldCharType') for n in part.iter(W+'fldChar')]}
    return model


def unmodified_parts(path):
    def signature(node):
        text = node.text or ''
        if not text.strip():
            text = ''
        return [node.tag, sorted(node.attrib.items()), text, [signature(child) for child in node]]
    result = {}
    with ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if (name in ('word/document.xml', 'docProps/core.xml', 'docProps/custom.xml')
                    or name.startswith(('word/header', 'word/footer')) and name.endswith('.xml')):
                continue
            content = archive.read(name)
            result[name] = signature(ET.fromstring(content)) if name.endswith(('.xml', '.rels')) else hashlib.sha256(content).hexdigest()
    return result


def first_difference(expected, actual, path='$'):
    if type(expected) is not type(actual):
        return path+' (type)'
    if isinstance(expected, dict):
        if expected.keys() != actual.keys():
            return path+' (keys)'
        for key in expected:
            result = first_difference(expected[key], actual[key], path+'.'+key)
            if result:
                return result
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            return path+' (length)'
        for i, (a, b) in enumerate(zip(expected, actual)):
            result = first_difference(a, b, f'{path}[{i}]')
            if result:
                return result
    elif expected != actual:
        return path+' (value)'
    return None


def make_plan(parts, values):
    clones, first, second, checks = [], [], [], []
    all_text = '\n'.join(text_values(values))+'\n'+'\n'.join(ptext(p) for part in parts.values() for p in part.iter(W+'p'))
    prefix = '__UTS_'+hashlib.sha256(all_text.encode('utf-8')).hexdigest()[:24]+'_'
    while prefix in all_text:
        prefix += 'X'
    scalar_counts = Counter()

    def replacement(path, key, value, count):
        marker = prefix+str(len(checks))+'__'
        first.append({'command': 'set', 'path': path, 'props': {'find': '{{'+key+'}}', 'replace': marker}})
        second.append({'command': 'set', 'path': path, 'props': {'find': marker, 'replace': scalar(value).replace('\n', '\v')}})
        checks.append({'path': path, 'token': key, 'count': count, 'marker': marker})

    for name, part in parts.items():
        root = part.find(W+'body') if name == 'word/document.xml' else part
        table_index = 0
        for node in root:
            if node.tag == W+'tbl':
                table_index += 1
                cap = caption(node)
                if cap.startswith('repeat:'):
                    if name != 'word/document.xml':
                        raise ValueError('Repeated header/footer tables are outside this profile')
                    rows = node.findall(W+'tr')
                    if len(rows) != 2 or any(cell.find(W+'tbl') is not None for cell in node.iter(W+'tc')):
                        raise ValueError('Unsupported repeated table shape')
                    collection = resolve(values, cap[7:])
                    if not collection:
                        raise ValueError('This profile requires at least one data row')
                    path = f'/body/tbl[{table_index}]'
                    # Append only: OfficeCLI 1.0.144 has different indexed-row insertion semantics.
                    clones.extend({'command': 'add', 'parent': path, 'from': path+'/tr[2]'} for _ in collection[1:])
                    tokens = Counter(m.group(1) for p in rows[1].iter(W+'p') for m in TOKEN.finditer(ptext(p)))
                    for index, row in enumerate(collection, 2):
                        for token, count in sorted(tokens.items()):
                            replacement(f'{path}/tr[{index}]', token, resolve(row, token), count)
                    for p in rows[0].iter(W+'p'):
                        scalar_counts.update(m.group(1) for m in TOKEN.finditer(ptext(p)))
                    continue
            for p in ([node] if node.tag == W+'p' else node.iter(W+'p')):
                scalar_counts.update(m.group(1) for m in TOKEN.finditer(ptext(p)))
    for token, count in sorted(scalar_counts.items()):
        replacement('/body', token, resolve(values, token), count)
    # Replace all original markers before inserting ANY user values, preventing recursive expansion.
    metadata = {'command': 'set', 'path': '/document', 'props': {
        'title': values['document']['title'], 'subject': values['document']['routine_id'],
        'creator': values['document']['author']}}
    return clones+first+second+[metadata], {'clones': len(clones), 'replacements': checks, 'prefix': prefix}


def execute_json(exe, arguments, timeout=120):
    environment = {**os.environ, 'OFFICECLI_NO_AUTO_RESIDENT': '1'}
    proc = subprocess.run([str(exe), *map(str, arguments)], capture_output=True, text=True,
                          encoding='utf-8', timeout=timeout, errors='strict', env=environment)
    try:
        reply = json.loads(proc.stdout)
    except (ValueError, TypeError) as exc:
        raise ValueError(f'OfficeCLI returned no valid JSON: {proc.stderr[:300]}') from exc
    if proc.returncode != 0 or reply.get('success') is not True:
        raise ValueError('OfficeCLI command failed: '+json.dumps(reply, ensure_ascii=False)[:1000])
    return reply


def full_batch_reply(reply):
    data = reply.get('data', {})
    if isinstance(data, dict) and data.get('outputFile'):
        path = Path(data['outputFile'])
        if not path.is_file() or path.stat().st_size > 20_000_000:
            raise ValueError('Invalid OfficeCLI batch receipt spill file')
        payload = json.loads(path.read_text(encoding='utf-8-sig'))
        data = payload.get('data', payload)
        reply = {'success': True, 'data': data}
    return reply


def verify_receipt(reply, commands, checks):
    data = reply.get('data', {})
    summary = data.get('summary', {})
    results = data.get('results', [])
    if (summary.get('total') != len(commands) or summary.get('succeeded') != len(commands)
            or summary.get('failed') != 0 or summary.get('skipped') != 0
            or len(results) != len(commands) or any(r.get('success') is not True for r in results)):
        raise ValueError('OfficeCLI did not complete every planned command')
    replacements = checks['replacements']
    for offset in (checks['clones'], checks['clones']+len(replacements)):
        for i, expected in enumerate(replacements):
            result = results[offset+i]
            match = re.search(r'\((\d+) matched\)\s*$', result.get('output', ''))
            if match is None or int(match.group(1)) != expected['count']:
                raise ValueError(f'Unexpected replacement count: {expected["path"]} {expected["token"]}')


def _build(source, schema, template, output, manifest, exe, data):
    check_xml_characters(data)
    values = context(data, source)
    parts = document_parts(template)
    expected = semantic_model(parts, values)
    commands, checks = make_plan(parts, values)
    stage = output.parent
    plan_path = stage/'officecli-commands.json'
    write_json(plan_path, commands)
    shutil.copyfile(template, output)
    reply = execute_json(exe, ['batch', output, '--input', plan_path, '--stop-on-error', '--json'])
    reply = full_batch_reply(reply)
    write_json(stage/'officecli-batch.json', reply)
    verify_receipt(reply, commands, checks)
    actual = semantic_model(document_parts(output))
    difference = first_difference(expected, actual)
    if difference:
        raise ValueError('Generated content or formatting differs from the fixed template contract: '+difference)
    if checks['prefix'] in json.dumps(actual, ensure_ascii=False):
        raise ValueError('Unresolved internal replacement marker')
    stable_parts = unmodified_parts(template)
    difference = first_difference(stable_parts, unmodified_parts(output))
    if difference:
        raise ValueError('Unexpected change to styles, relationships or other fixed package parts: '+difference)
    dc = '{http://purl.org/dc/elements/1.1/}'
    with ZipFile(output) as archive:
        core = ET.fromstring(archive.read('docProps/core.xml'))
    metadata = {key: core.findtext(dc+key, '') for key in ('title', 'subject', 'creator')}
    expected_metadata = {'title': data['document']['title'], 'subject': data['document']['routine_id'],
                         'creator': data['document']['author']}
    if metadata != expected_metadata:
        raise ValueError('Document properties differ from the canonical specification')
    actual['_document_properties'] = metadata
    actual['_unmodified_parts'] = stable_parts
    semantic_sha = hashlib.sha256(json.dumps(actual, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    validation = execute_json(exe, ['validate', output, '--json'])
    write_json(stage/'officecli-validation.json', validation)
    check = {'status': 'passed', 'template_content_and_formatting': 'matched',
             'unchanged_package_parts': len(stable_parts),
             'field_codes': {name: info['field_codes'] for name, info in actual.items() if 'field_codes' in info},
             'commands': len(commands), 'repeated_rows_cloned': checks['clones'],
             'semantic_sha256': semantic_sha}
    write_json(stage/'content-check.json', check)
    return {'generator_backend': 'officecli', 'generator_version': '0.2.0',
            'source': source.name, 'source_sha256': sha(source), 'schema_sha256': sha(schema),
            'template_sha256': sha(template), 'output': output.name, 'output_sha256': sha(output),
            'status': data['document']['status'], 'semantic_sha256': semantic_sha,
            'content_check': check, 'visual_review': 'not_performed_by_this_command'}


def build(source, schema, template, output, manifest, exe, data):
    try:
        return _build(source, schema, template, output, manifest, exe, data)
    finally:
        if output.exists():
            # validate may otherwise create a resident that retains the file for 60s.
            reply = execute_json(exe, ['close', output, '--json'])
            write_json(output.parent/'officecli-close.json', reply)
