"""One-time v02 template maintenance, all edits through approved OfficeCLI.

Copies the retained v01 template, then changes contract prose through text
commands. Python reads XML only for audit; it never creates OOXML.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
from xml.etree import ElementTree as ET
from zipfile import ZipFile
HERE=Path(__file__).resolve().parent
SKILL=HERE.parents[1]/'skills/routine-unit-test-spec'
SOURCE=SKILL/'assets/templates/unit-test-spec-v01.docx'
OUTPUT=SKILL/'assets/templates/unit-test-spec-v02.docx'
OFFICE=Path(r'C:/Users/stell/AppData/Local/Programs/IBM Bob/resources/app/extensions/bob-code/dist/officecli.exe')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name, value): (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if OUTPUT.exists(): raise FileExistsError('One-time template build refuses overwrite')
assert sha(OFFICE)=='eec03daa7978a1e8f28a4ee0ce910ef9e3cb355d26a7fa4afcecadfe34693fbb'
source_sha=sha(SOURCE)
changes=[('JSON契約 0.1.0','JSON契約 0.2.0'),
 ('repeatは同じ入力を繰り返す回数を示す。iterationはk=1..repeatの各呼出しで照合する。preserveは呼出し前の値を保持する。all_valid_bytesは有効な全オブジェクト領域の全バイトを保持する。','repeatは同じ操作の呼出し回数を示す。初期条件、操作、入力、比較名、期待値と注記は原仕様に基づく記述データである。実際の結果は別の実施記録に残す。'),
 ('固定された仕様IDまたはJSON Pointerを基準に、動的試験、レビュー、呼出し側責務と対象外の理由を示す。','対象となる原仕様の宣言IDまたはJSON Pointerを基準に、試験、レビュー、未検証、呼出し側責務と範囲外の理由を示す。')]
commands=[{'command':'set','path':'/body','props':{'find':old,'replace':new}} for old,new in changes]
commands.append({'command':'set','path':'/document','props':{'title':'汎用単体テスト仕様書テンプレート 0.2.0','subject':'Generic finite JSON unit-test contract','creator':'Codex template maintenance'}})
save('commands.json',commands)
shutil.copyfile(SOURCE,OUTPUT)
env={**os.environ,'OFFICECLI_NO_AUTO_RESIDENT':'1'}
invocations=[]
def run(label,args):
 p=subprocess.run([str(OFFICE),*map(str,args)],capture_output=True,text=True,encoding='utf-8-sig',timeout=180,env=env)
 (HERE/(label+'.stdout.json')).write_text(p.stdout,encoding='utf-8')
 (HERE/(label+'.stderr.txt')).write_text(p.stderr,encoding='utf-8')
 invocations.append({'label':label,'argv':[str(OFFICE),*map(str,args)],'exit_code':p.returncode})
 save('invocations.json',invocations)
 result=json.loads(p.stdout)
 assert p.returncode==0 and result.get('success') is True,result
 return result
try:
 reply=run('batch',['batch',OUTPUT,'--input',HERE/'commands.json','--stop-on-error','--json'])
 data=reply.get('data',{})
 if data.get('outputFile'): data=json.loads(Path(data['outputFile']).read_text(encoding='utf-8-sig')).get('data',{})
 save('batch-full.json',data)
 assert len(data['results'])==len(commands) and all(r.get('success') is True for r in data['results'])
 validation=run('validate',['validate',OUTPUT,'--json'])
 with ZipFile(OUTPUT) as z:
  document=ET.fromstring(z.read('word/document.xml'))
  w='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
  tables=list(document.iter(w+'tbl'))
  assert len(tables)==8
  for table in tables:
   assert len(table.findall(w+'tr'))==2
   assert table.find(w+'tr/'+w+'trPr/'+w+'tblHeader') is not None
   assert not table.findall('.//'+w+'trHeight')
  text=''.join(document.itertext())
  assert 'JSON契約 0.2.0' in text and 'all_valid_bytes' not in text
 save('audit.json',{'template_sha256':sha(OUTPUT),'source_sha256':source_sha,'source_unchanged':sha(SOURCE)==source_sha,
                    'tables':8,'repeated_headers':True,'variable_row_height':True,'officecli_validation':validation,
                    'visual_review':'not_performed','bob_execution':'not_tested','python_ooxml_write':False})
finally: run('close',['close',OUTPUT,'--json'])
print(json.dumps({'status':'built_once','template':str(OUTPUT),'sha256':sha(OUTPUT)}))
