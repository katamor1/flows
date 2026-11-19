"""Export a Word decision sheet and import a deterministic JSON review context."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
FORMAT = 'routine-decisions-v1'
HEADERS = ['項目ID', '未決事項', '状態', '決定内容']
TITLE = '仕様の決定票'
INSTRUCTIONS = '状態と決定内容の欄を編集してください。状態は未決・保留・決定のいずれかです。決定には回答の入力が必要です。'
MAX_XML_BYTES = 8 * 1024 * 1024


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f'JSONキーの重複: {key}')
        obj[key] = value
    return obj


def load_source(path):
    raw = path.read_bytes()
    spec = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(spec, dict) or not isinstance(spec.get('document'), dict):
        raise ValueError('document が必要です')
    document_id = spec['document'].get('id')
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError('document.id が必要です')
    issues = spec.get('open_issues')
    if not isinstance(issues, list):
        raise ValueError('open_issues の配列が必要です')
    seen = set()
    for item in issues:
        item_id = item.get('id') if isinstance(item, dict) else None
        if not isinstance(item_id, str) or not item_id.strip() or item_id in seen:
            raise ValueError('未決事項には空欄でない一意の id が必要です')
        seen.add(item_id)
    return spec, hashlib.sha256(raw).hexdigest()


def expected_rows(spec, source_hash):
    rows = [
        ['書式', FORMAT, '', ''],
        ['仕様ID', spec['document']['id'], '', ''],
        ['仕様 SHA-256', source_hash, '', ''],
        HEADERS,
    ]
    for issue in spec['open_issues']:
        # Display the source fields in a stable order without depending on a sample schema.
        context = {key: value for key, value in issue.items() if key != 'id'}
        description = json.dumps(context, ensure_ascii=False, sort_keys=True, allow_nan=False)
        rows.append([issue['id'], description, '未決', ''])
    return rows


def read_cell(cell):
    paragraphs = []
    for child in cell:
        if child.tag == W + 'tcPr':
            continue
        if child.tag != W + 'p':
            raise ValueError('決定票のセルは通常のテキスト段落だけで構成してください')
        parts = []
        for run in child:
            if run.tag in {W + name for name in ('pPr', 'proofErr', 'bookmarkStart', 'bookmarkEnd')}:
                continue
            if run.tag != W + 'r':
                raise ValueError('コメント、フィールド、変更履歴を本文から除いてください')
            for item in run:
                if item.tag == W + 't' and not len(item):
                    parts.append(item.text or '')
                elif item.tag == W + 'tab':
                    parts.append('\t')
                elif item.tag == W + 'cr' or (item.tag == W + 'br' and item.get(W + 'type', 'textWrapping') == 'textWrapping'):
                    parts.append('\n')
                elif item.tag != W + 'rPr':
                    raise ValueError('決定票のセルはテキストだけを受け付けます')
        paragraphs.append(''.join(parts))
    if not paragraphs:
        raise ValueError('段落のないセルです')
    return '\n'.join(paragraphs)


def read_rows(path):
    if path.suffix.lower() != '.docx':
        raise ValueError('決定票には .docx を指定してください')
    with ZipFile(path) as archive:
        members = [part for part in archive.infolist() if part.filename == 'word/document.xml']
        if len(members) != 1 or members[0].file_size > MAX_XML_BYTES:
            raise ValueError('Word本文がないか、重複または上限超過です')
        data = archive.read(members[0])
    # The supported part is UTF-8 WordprocessingML. Do not consume XML declarations
    # with other encodings or custom entities.
    xml = data.decode('utf-8-sig')
    if '<!DOCTYPE' in xml or '<!ENTITY' in xml:
        raise ValueError('Word本文にDTDまたは独自エンティティがあります')
    body = ET.fromstring(xml).find(W + 'body')
    if body is None:
        raise ValueError('Word本文がありません')
    disallowed = {'ins', 'del', 'moveFrom', 'moveTo', 'cellIns', 'cellDel',
                  'cellMerge', 'gridSpan', 'vMerge', 'hMerge', 'vanish'}
    for node in body.iter():
        name = node.tag.removeprefix(W)
        if name in disallowed or name.endswith('PrChange') or name.startswith(('moveFromRange', 'moveToRange')):
            raise ValueError('変更履歴、結合セル、隠し文字を除いてください')
    tables = list(body.iter(W + 'tbl'))
    if len(tables) != 1 or tables[0] not in list(body):
        raise ValueError('決定票に必要な表は1つです')
    table = tables[0]
    rows = []
    for row in table:
        if row.tag in {W + 'tblPr', W + 'tblGrid'}:
            continue
        if row.tag != W + 'tr':
            raise ValueError('決定票の行構造が変更されています')
        cells = []
        for cell in row:
            if cell.tag in {W + 'trPr', W + 'tblPrEx'}:
                continue
            if cell.tag != W + 'tc':
                raise ValueError('決定票のセル構造が変更されています')
            cells.append(read_cell(cell))
        rows.append(cells)
    return rows


def review_context(spec, source_hash, rows):
    expected = expected_rows(spec, source_hash)
    if len(rows) != len(expected) or rows[:4] != expected[:4]:
        raise ValueError('書式、仕様ID、元の仕様のハッシュ、行件数のいずれかが一致しません')
    decisions = []
    pending = []
    for row, original in zip(rows[4:], expected[4:]):
        if len(row) != 4 or row[:2] != original[:2]:
            raise ValueError(f'項目IDまたは説明が変更されています: {original[0]}')
        item_id, _, state, answer = row
        if state not in {'未決', '保留', '決定'}:
            raise ValueError(f'{item_id}: 状態は未決・保留・決定のいずれかです')
        if state == '決定':
            if not answer.strip():
                raise ValueError(f'{item_id}: 決定内容を入力してください')
            decisions.append({'issue_id': item_id, 'decision': answer})
        else:
            if state == '未決' and answer.strip():
                raise ValueError(f'{item_id}: 回答がある場合は決定または保留を指定してください')
            pending.append({'issue_id': item_id, 'state': state, 'note': answer})
    return {
        'format': FORMAT, 'source_sha256': source_hash, 'specification': spec,
        'decisions': decisions, 'pending_issues': pending,
        'reevaluation_status': 'required' if decisions else 'no_decisions',
    }


def export_sheet(officecli, spec, source_hash, output):
    if output.suffix.lower() != '.docx':
        raise ValueError('出力には .docx を指定してください')
    rows = expected_rows(spec, source_hash)
    commands = [
        {'command': 'add', 'parent': '/body', 'type': 'paragraph', 'props': {'text': TITLE, 'style': 'Title'}},
        {'command': 'add', 'parent': '/body', 'type': 'paragraph', 'props': {'text': INSTRUCTIONS}},
        {'command': 'add', 'parent': '/body', 'type': 'table',
         'props': {'rows': str(len(rows)), 'cols': '4', 'width': '100%', 'style': 'TableGrid'}},
    ]
    for ri, row in enumerate(rows, 1):
        for ci, text in enumerate(row, 1):
            props = {'text': text}
            if ri >= 5 and ci >= 3:
                props['shd'] = 'EAF2F8'
            commands.append({'command': 'set', 'path': f'/body/tbl[1]/tr[{ri}]/tc[{ci}]', 'props': props})
    env = dict(os.environ, OFFICECLI_NO_AUTO_RESIDENT='1')

    def invoke(*arguments):
        result = subprocess.run([str(officecli), *map(str, arguments)], capture_output=True, env=env, timeout=120)
        if result.returncode:
            raise ValueError(result.stderr.decode('utf-8', errors='replace') or result.stdout.decode('utf-8', errors='replace'))

    with TemporaryDirectory(dir=output.parent) as folder:
        temp = Path(folder) / 'decision-sheet.docx'
        batch = Path(folder) / 'commands.json'
        batch.write_bytes(canonical(commands))
        invoke('create', temp)
        try:
            invoke('batch', temp, '--input', batch, '--json')
        finally:
            invoke('close', temp, '--json')
        if read_rows(temp) != rows:
            raise ValueError('OfficeCLI出力の表内容と入力が一致しません')
        with output.open('xb') as stream:
            stream.write(temp.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    export = actions.add_parser('export')
    export.add_argument('--officecli', type=Path, required=True)
    load = actions.add_parser('import')
    load.add_argument('--word', type=Path, required=True)
    for action in (export, load):
        action.add_argument('--spec', type=Path, required=True)
        action.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.out.exists():
            raise ValueError('出力先が既に存在します')
        spec, source_hash = load_source(args.spec)
        if args.action == 'export':
            export_sheet(args.officecli.resolve(strict=True), spec, source_hash, args.out.resolve())
        else:
            content = canonical(review_context(spec, source_hash, read_rows(args.word)))
            with args.out.open('xb') as stream:
                stream.write(content)
    except (ValueError, OSError, BadZipFile, ET.ParseError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
