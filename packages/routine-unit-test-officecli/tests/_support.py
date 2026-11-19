import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
PACKAGE=Path(__file__).resolve().parents[1]
SKILL=PACKAGE/'skills/routine-unit-test-spec'
WORKSPACE=PACKAGE.parents[1]
OFFICE=os.environ.get('UT_OFFICECLI')
CODE_JOB=WORKSPACE/'artifacts/routine-generic-validation/pipeline-code/range-clamp'
def new_test_root(prefix):
 parent=WORKSPACE/'artifacts/routine-generic-validation/unit-tests/checks';parent.mkdir(parents=True,exist_ok=True)
 return Path(tempfile.mkdtemp(prefix=prefix,dir=parent)).resolve()
def cli(skill,*args):
 return subprocess.run([sys.executable,'-X','utf8','-S','-B',str(skill/'scripts/utflow.py'),*map(str,args),'--officecli',OFFICE],capture_output=True,text=True,encoding='utf-8',timeout=240,shell=False)
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p,data): p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def explicit(skill,name):
 folder=skill/'assets/examples'/name
 source,header=('RangeClamp.c','RangeClamp.h') if name=='range-clamp' else ('SampleHold_Update.c','SampleHold_Update.h')
 return ('--program-spec',folder/'program-spec.json','--source',folder/source,'--header',folder/header,'--unit-test-spec',folder/'unit-test-spec.json')
