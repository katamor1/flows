"""One-time maintainer build of v02. All DOCX writes are OfficeCLI commands."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
SKILL = HERE.parents[1]/'skills/routine-spec-doc'
OFFICE = Path('C:/Users/stell/AppData/Local/Programs/IBM Bob/resources/app/extensions/bob-code/dist/officecli.exe')
SOURCE = SKILL/'assets/templates/routine-spec-v01.docx'
TARGET = SKILL/'assets/templates/routine-spec-v02.docx'


def run(label, args):
    p = subprocess.run([str(OFFICE), *map(str, args)], capture_output=True, encoding='utf-8',
                       env={**os.environ, 'OFFICECLI_NO_AUTO_RESIDENT': '1'})
    (HERE/(label+'.stdout.json')).write_text(p.stdout, encoding='utf-8')
    (HERE/(label+'.stderr.txt')).write_text(p.stderr, encoding='utf-8')
    reply = json.loads(p.stdout)
    if p.returncode or reply.get('success') is not True:
        raise ValueError(label+' failed: '+p.stdout[:1000])
    return reply


def main():
    if TARGET.exists():
        raise ValueError('Template already built; maintainer must choose a new revision')
    commands = []
    for table, cap in {2:'view.assumptions',3:'view.parameters',4:'view.state_fields',
                       5:'view.results',6:'view.steps',7:'view.decisions',8:'view.returns',
                       9:'view.constraints',10:'view.examples',11:'view.traceability',12:'view.issues'}.items():
        commands.append({'command':'set','path':f'/body/tbl[{table}]','props':{'caption':'repeat:'+cap}})
    # Remove virtual columns through OfficeCLI, preserving the inherited table style.
    for column in (5,4,3):
        commands.append({'command':'remove','path':f'/body/tbl[7]/col[{column}]'})
    commands += [
        {'command':'set','path':'/body/tbl[7]/tr[1]/tc[2]/p[1]','props':{'text':'項目と値'}},
        {'command':'set','path':'/body/tbl[7]/tr[2]/tc[2]/p[1]','props':{'text':'{{details}}'}},
    ]
    for row in (1,2):
        for column, width in ((1,'2700'),(2,'6600')):
            commands.append({'command':'set','path':f'/body/tbl[7]/tr[{row}]/tc[{column}]','props':{'width':width}})
    for p, text in {
        2:'{{document.status_label}}  |  {{document.date}}\v状態 {{document.status}}  スキーマ {{schema_version}}  テンプレート {{document.template_id}}\v作成者 {{document.author}}',
        6:'{{overview.scope}}\v担当範囲 {{overview.coverage}}',
        7:'2 前提',
        13:'{{view.type_definitions}}',
        16:'5 処理手順と条件表',
        18:'設定\v{{view.configuration_text}}',
    }.items():
        commands.append({'command':'set','path':f'/body/p[{p}]','props':{'text':text}})
    # The state type is rendered with its name by the display adapter.
    plan = HERE/'commands.json'
    plan.write_text(json.dumps(commands, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    original = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    shutil.copyfile(SOURCE,TARGET)
    try:
        batch=run('batch',['batch',TARGET,'--input',plan,'--stop-on-error','--json'])
        validation=run('validation',['validate',TARGET,'--json'])
    finally:
        run('close',['close',TARGET,'--json'])
    with ZipFile(TARGET) as z:
        root=ET.fromstring(z.read('word/document.xml'))
    w='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    tables=root.findall(w+'body/'+w+'tbl')
    assert len(tables)==12 and all(len(row.findall(w+'tc'))==2 for row in tables[6].findall(w+'tr'))
    record={'source':SOURCE.name,'source_sha256':original,
            'source_unchanged':original==hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'target':TARGET.name,'target_sha256':hashlib.sha256(TARGET.read_bytes()).hexdigest(),
            'officecli_sha256':hashlib.sha256(OFFICE.read_bytes()).hexdigest(),
            'commands':len(commands),'validation_success':validation['success'],
            'docx_author':'OfficeCLI only','python_xml':'read-only inspection',
            'visual_review':'not_performed'}
    (HERE/'evidence.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False))


if __name__=='__main__':
    main()
