"""One-time fixed-template build. Only OfficeCLI writes DOCX internals.

Python reads the predecessor package, builds XML *instructions*, copies the
predecessor, and records verification. It never opens any ZIP in write mode.
The operation marker must be run once immediately before --apply.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from xml.etree import ElementTree as ET
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = ROOT / 'packages/routine-spec-officecli/skills/routine-spec-doc/assets/templates/routine-spec-v01.docx'
OUTPUT = ROOT / 'packages/routine-unit-test-officecli/skills/routine-unit-test-spec/assets/templates/unit-test-spec-v01.docx'
OFFICECLI = Path(r'C:\Users\stell\AppData\Local\Programs\IBM Bob\resources\app\extensions\bob-code\dist\officecli.exe')
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS = {'w': W}
ET.register_namespace('w', W)
ET.register_namespace('r', R)
WIDTH = 9866


def el(name, **attrs):
    return ET.Element('{'+W+'}'+name, {'{'+W+'}'+key: str(value) for key, value in attrs.items()})


def add(parent, name, **attrs):
    child = el(name, **attrs)
    parent.append(child)
    return child


def rpr(size=21, bold=False):
    node = el('rPr')
    add(node, 'rFonts', ascii='Yu Gothic', hAnsi='Yu Gothic', eastAsia='Yu Gothic', cs='Yu Gothic')
    if bold:
        add(node, 'b')
    add(node, 'color', val='000000')
    add(node, 'sz', val=size)
    add(node, 'szCs', val=size)
    add(node, 'lang', val='ja-JP', eastAsia='ja-JP')
    return node


def paragraph(text='', style='Normal', *, cell=False, bold=False, size=21, page=False):
    node = el('p')
    pp = add(node, 'pPr')
    add(pp, 'pStyle', val=style)
    if style in ('Title', 'Heading1', 'Heading2'):
        add(pp, 'keepNext')
        add(pp, 'keepLines')
    if page:
        add(pp, 'pageBreakBefore')
    add(pp, 'widowControl')
    add(pp, 'snapToGrid', val=0)
    add(pp, 'spacing', before=0, after=40 if cell else 100, line=260, lineRule='auto')
    run = add(node, 'r')
    run.append(rpr(size, bold))
    t = add(run, 't')
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = text
    return node


def table(name, headers, keys, widths):
    assert sum(widths) == WIDTH
    node = el('tbl')
    props = add(node, 'tblPr')
    add(props, 'tblW', w=WIDTH, type='dxa')
    add(props, 'jc', val='left')
    borders = add(props, 'tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        add(borders, edge, val='single', sz=4, color='CDD5DF')
    add(props, 'tblLayout', type='fixed')
    margins = add(props, 'tblCellMar')
    for edge, width in (('top', 80), ('left', 100), ('bottom', 80), ('right', 100)):
        add(margins, edge, w=width, type='dxa')
    add(props, 'tblCaption', val='repeat:view.'+name)
    add(props, 'tblDescription', val='見出し行と可変高さの繰返し明細行')
    grid = add(node, 'tblGrid')
    for width in widths:
        add(grid, 'gridCol', w=width)
    for row_index, values in enumerate((headers, ['{{'+key+'}}' for key in keys])):
        row = add(node, 'tr')
        if row_index == 0:
            rp = add(row, 'trPr')
            add(rp, 'tblHeader')
        for text, width in zip(values, widths):
            cell = add(row, 'tc')
            cp = add(cell, 'tcPr')
            add(cp, 'tcW', w=width, type='dxa')
            if row_index == 0:
                add(cp, 'shd', val='clear', fill='E7EFF8', color='auto')
            add(cp, 'vAlign', val='top')
            cell.append(paragraph(text, cell=True, bold=row_index == 0))
    return node


TABLES = [
    ('environment', ['環境と実施条件'], ['text'], [WIDTH]),
    ('assumptions', ['仮定ID', '内容'], ['id', 'text'], [1500, 8366]),
    ('case_index', ['ケースID', '試験項目', '目的と判定基準', '根拠', '実施状態'], ['id', 'title', 'purpose', 'refs', 'status'], [1500, 1950, 3300, 2016, 1100]),
    ('case_steps', ['ケースID 手順', '初期条件と入力', '期待結果と判定', '根拠'], ['case_step', 'inputs', 'expected', 'refs'], [1550, 3400, 3200, 1716]),
    ('families', ['族ID', '定義と実施方法', '期待値規則', '根拠'], ['id', 'definition', 'oracle', 'refs'], [1550, 3800, 2800, 1716]),
    ('static_checks', ['確認ID', '確認方法と対象範囲', '判定基準', '根拠'], ['id', 'method', 'criterion', 'refs'], [1550, 3500, 3100, 1716]),
    ('coverage', ['仕様参照', '確認方法', '対応項目ID', '割当理由'], ['ref', 'method', 'items', 'reason'], [2350, 1400, 2400, 3716]),
    ('open_issues', ['課題ID', '決定者', '未決事項と判断内容'], ['id', 'owner', 'decision'], [1500, 1800, 6566]),
]


def make_body(source):
    with ZipFile(source) as archive:
        old = ET.fromstring(archive.read('word/document.xml'))
    section = deepcopy(old.find('w:body/w:sectPr', NS))
    size = section.find('w:pgSz', NS)
    size.attrib.clear()
    size.set('{'+W+'}w', '11906')
    size.set('{'+W+'}h', '16838')
    margins = section.find('w:pgMar', NS)
    for key, value in {'top':1020, 'right':1020, 'bottom':1020, 'left':1020, 'header':420, 'footer':420, 'gutter':0}.items():
        margins.set('{'+W+'}'+key, str(value))
    body = el('body')
    body.append(paragraph('{{document.title}}', 'Title', size=34))
    body.append(paragraph('{{document.status_label}}', bold=True, size=23))
    body.append(paragraph('文書ID {{document.id}}    版 {{document.revision}}    作成日 {{document.date}}'))
    body.append(paragraph('作成者 {{document.author}}    状態 {{document.status}}'))
    body.append(paragraph('対象 {{document.routine_id}}    {{document.routine_name}}'))
    body.append(paragraph('テンプレート {{document.template_id}}    JSON契約 0.1.0'))
    body.append(paragraph('{{view.not_executed}}'))
    body.append(paragraph('1 試験の目的と概要', 'Heading1', bold=True, size=27))
    body.append(paragraph('{{summary}}'))
    body.append(paragraph('2 対象と固定入力', 'Heading1', bold=True, size=27))
    body.append(paragraph('{{view.target_summary}}'))
    body.append(paragraph('3 試験環境', 'Heading1', bold=True, size=27))
    body.append(table(*TABLES[0]))
    body.append(paragraph('4 前提と未承認の仮定', 'Heading1', bold=True, size=27))
    body.append(table(*TABLES[1]))
    sections = [
        ('5 ケース一覧', 2, True, '各ケースは固有の初期条件から独立して実施する。実際の結果と証跡は実施記録に記入する。'),
        ('6 ケースの詳細手順', 3, True, 'repeatは同じ入力を繰り返す回数を示す。iterationはk=1..repeatの各呼出しで照合する。preserveは呼出し前の値を保持する。all_valid_bytesは有効な全オブジェクト領域の全バイトを保持する。'),
        ('7 パラメータ族', 4, True, '組合せ数と呼出し照合数を区別する。全系列を文書へ展開せず、有限集合、列挙順、期待値規則と代表例を定義する。'),
        ('8 静的確認', 5, True, '各確認項目は未実施である。動的な戻り値の照合だけでは証明できない制約をレビューする。'),
        ('9 仕様と確認項目の対応', 6, True, '固定された仕様IDまたはJSON Pointerを基準に、動的試験、レビュー、呼出し側責務と対象外の理由を示す。'),
        ('10 未決事項', 7, False, '要求の承認と試験の実施状態を分け、未決事項の判断内容を引き継ぐ。'),
    ]
    for title, index, page, explanation in sections:
        body.append(paragraph(title, 'Heading1', bold=True, size=27, page=page))
        body.append(paragraph(explanation))
        body.append(table(*TABLES[index]))
    body.append(paragraph())
    body.append(section)
    return body


def make_styles(source):
    with ZipFile(source) as archive:
        root = ET.fromstring(archive.read('word/styles.xml'))
    values = [('Normal',21,False), ('Title',34,False), ('Heading1',27,True), ('Heading2',24,True), ('Header',18,False), ('Footer',18,False)]
    for name, size, bold in values:
        old = root.find('w:style[@w:styleId="'+name+'"]', NS)
        if old is None:
            old = el('style', type='paragraph', styleId=name)
            root.append(old)
        for child in list(old):
            old.remove(child)
        add(old, 'name', val=name)
        if name != 'Normal':
            add(old, 'basedOn', val='Normal')
        add(old, 'next', val='Normal')
        add(old, 'qFormat')
        pp = add(old, 'pPr')
        if name in ('Title','Heading1','Heading2'):
            add(pp, 'keepNext')
            add(pp, 'keepLines')
        add(pp, 'snapToGrid', val=0)
        add(pp, 'spacing', before=180 if name.startswith('Heading') else 0, after=100, line=260, lineRule='auto')
        if name.startswith('Heading'):
            add(pp, 'outlineLvl', val=int(name[-1])-1)
        old.append(rpr(size, bold))
    return root


def make_header():
    root = el('hdr')
    root.append(paragraph('{{document.id}}    {{document.routine_name}}', 'Header', size=18))
    return root


def make_footer():
    root = el('ftr')
    p = paragraph('Rev {{document.revision}}    {{document.status_label}}    ', 'Footer', size=18)
    add(p.find('w:pPr', NS), 'jc', val='right')
    for code, trailing in [('PAGE', ' / '), ('NUMPAGES', '')]:
        field = add(p, 'fldSimple', instr=code)
        run = add(field, 'r')
        run.append(rpr(18))
        add(run, 't').text = '1'
        if trailing:
            run = add(p, 'r')
            run.append(rpr(18))
            t = add(run, 't')
            t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            t.text = trailing
    root.append(p)
    return root


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(name, value):
    (HERE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def audit(path):
    with ZipFile(path) as archive:
        parts = {n: ET.fromstring(archive.read(n)) for n in ['word/document.xml','word/styles.xml','word/header1.xml','word/footer1.xml']}
    document = parts['word/document.xml']
    tables = []
    for tbl in document.iter('{'+W+'}tbl'):
        caption = tbl.find('w:tblPr/w:tblCaption', NS).get('{'+W+'}val')
        rows = tbl.findall('w:tr', NS)
        assert len(rows) == 2
        assert rows[0].find('w:trPr/w:tblHeader', NS) is not None
        assert not tbl.findall('.//w:tc/w:tbl', NS)
        assert not tbl.findall('.//w:trHeight', NS)
        keys = re.findall(r'\{\{([^{}]+)\}\}', ''.join(rows[1].itertext()))
        tables.append({'caption':caption, 'cells_per_row':[len(r.findall('w:tc',NS)) for r in rows], 'prototype_tokens':keys, 'repeat_header':True, 'variable_height':True})
    assert [t['caption'] for t in tables] == ['repeat:view.'+t[0] for t in TABLES]
    for actual, spec in zip(tables, TABLES):
        assert actual['prototype_tokens'] == spec[2]
    tokens = {n: re.findall(r'\{\{([^{}]+)\}\}', ''.join(root.itertext())) for n, root in parts.items() if n != 'word/styles.xml'}
    fields = [n.get('{'+W+'}instr') for n in parts['word/footer1.xml'].iter('{'+W+'}fldSimple')]
    assert fields == ['PAGE','NUMPAGES']
    assert 'document.id' in tokens['word/header1.xml']
    section = document.find('w:body/w:sectPr', NS)
    assert section.find('w:pgSz',NS).get('{'+W+'}w') == '11906'
    assert section.find('w:pgSz',NS).get('{'+W+'}h') == '16838'
    for part in ('word/document.xml','word/header1.xml','word/footer1.xml'):
        assert '\ufffd' not in ''.join(parts[part].itertext())
    return {'template_sha256':sha(path), 'tables':tables, 'tokens':tokens, 'footer_fields':fields,
            'page':'A4 portrait', 'body_font_pt':10.5, 'body_font':'Yu Gothic', 'visual_qa':'pending integration render by root'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    commands = []
    for part, xpath, element in [('/document','/w:document/w:body',make_body(SOURCE)),('/styles','/w:styles',make_styles(SOURCE)),('/header[1]','/w:hdr',make_header()),('/footer[1]','/w:ftr',make_footer())]:
        commands.append({'command':'raw-set','part':part,'xpath':xpath,'action':'replace','xml':ET.tostring(element,encoding='unicode')})
    record('template-commands.json', commands)
    if not args.apply:
        print(json.dumps({'planned_commands':len(commands),'output':str(OUTPUT)}))
        return
    if OUTPUT.exists():
        raise FileExistsError('One-time build refuses to overwrite the retained template')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    before = sha(SOURCE)
    shutil.copyfile(SOURCE, OUTPUT)
    temporary = HERE/'tmp'
    temporary.mkdir(exist_ok=True)
    env = {**os.environ,'OFFICECLI_NO_AUTO_RESIDENT':'1','TMP':str(temporary),'TEMP':str(temporary)}
    invocations = []
    def run(label, arguments):
        proc = subprocess.run([str(OFFICECLI),*map(str,arguments)],capture_output=True,encoding='utf-8-sig',env=env,timeout=180)
        (HERE/(label+'.stdout.json')).write_text(proc.stdout,encoding='utf-8')
        (HERE/(label+'.stderr.txt')).write_text(proc.stderr,encoding='utf-8')
        invocations.append({'label':label,'argv':[str(OFFICECLI),*map(str,arguments)],'exit_code':proc.returncode,'no_auto_resident':True})
        record('officecli-invocations.json', invocations)
        result = json.loads(proc.stdout)
        if proc.returncode or result.get('success') is not True:
            raise RuntimeError('OfficeCLI '+label+' failed; inspect recorded response')
        return result
    try:
        receipt = run('template-batch',['batch',OUTPUT,'--input',HERE/'template-commands.json','--stop-on-error','--json'])
        data = receipt.get('data',{})
        if data.get('outputFile'):
            payload = json.loads(Path(data['outputFile']).read_text(encoding='utf-8-sig'))
            data = payload.get('data',payload)
        record('template-batch.full.json', data)
        if len(data.get('results',[])) != len(commands) or any(r.get('success') is not True for r in data['results']):
            raise AssertionError('Incomplete batch receipt')
        validation = run('validate-template',['validate',OUTPUT,'--json'])
        record('template-audit.json', {**audit(OUTPUT),'source':str(SOURCE),'source_sha256':before,'source_unchanged':before==sha(SOURCE),'officecli_validation':validation})
    finally:
        run('close-template',['close',OUTPUT,'--json'])
    print(json.dumps({'template':str(OUTPUT),'sha256':sha(OUTPUT),'validation':'success','commands':len(commands)}))


if __name__ == '__main__':
    main()
