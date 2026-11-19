"""Final project handoff runs. No test execution or visual approval is inferred."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[3]
SKILL=ROOT/'packages/routine-unit-test-officecli/skills/routine-unit-test-spec'
OUT=ROOT/'artifacts/routine-generic-validation/unit-tests'
OFFICE=Path(r'C:/Users/stell/AppData/Local/Programs/IBM Bob/resources/app/extensions/bob-code/dist/officecli.exe')
CODE=ROOT/'artifacts/routine-generic-validation/pipeline-code/range-clamp'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
results=[]
def run(label,*args):
 command=[sys.executable,'-X','utf8','-S','-B',str(SKILL/'scripts/utflow.py'),*map(str,args),'--officecli',str(OFFICE)]
 start=time.monotonic();p=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=240)
 (OUT/(label+'.stdout.json')).write_text(p.stdout,encoding='utf-8');(OUT/(label+'.stderr.txt')).write_text(p.stderr,encoding='utf-8')
 receipt={'label':label,'argv':command,'exit_code':p.returncode,'elapsed_seconds':round(time.monotonic()-start,3)}
 results.append(receipt);save(OUT/'final-invocations.json',results)
 if p.returncode:raise RuntimeError(label+': '+p.stderr)
 return json.loads(p.stdout)
for example,job in [('range-clamp','range-clamp-release-final'),('sample-hold','sample-hold-release-final'),('alarm-regression','alarm-regression-release-final')]:
 folder=SKILL/'assets/examples'/example
 if example=='range-clamp':inputs=['--code-job',CODE]
 elif example=='alarm-regression':inputs=['--code-job',ROOT/'prototypes/routine-code-poc']
 else:inputs=['--program-spec',folder/'program-spec.json','--source',folder/'SampleHold_Update.c','--header',folder/'SampleHold_Update.h']
 run(job+'-new','new-job',*inputs,'--unit-test-spec',folder/'unit-test-spec.json','--workspace',OUT,'--job',job)
 run(job+'-validate','validate','--workspace',OUT,'--job',job)
 run(job+'-render','render','--workspace',OUT,'--job',job,'--run','r001')
run('doctor-final','doctor')
summaries=[]
for job in ('range-clamp-release-final','sample-hold-release-final','alarm-regression-release-final'):
 folder=OUT/job;render=folder/'renders/r001';trace=load(render/'traceability.json');manifest=load(render/'manifest.json')
 assert load(render/'content-check.json')['status']=='passed'
 assert all(x['status']=='not_executed' and x['evidence']==[] for x in load(render/'execution-record.json')['results'])
 summaries.append({'job':job,'document':str(render/'unit-test-spec.docx'),'manifest':str(render/'manifest.json'),
                   'canonical_sha256':sha(folder/'source/unit-test-spec.json'),'counts':trace['counts'],
                   'target':trace['target'],'input_provenance':manifest['input_provenance'],'content_and_formatting':'matched',
                   'structural_validation':'OfficeCLI success','execution':'not_executed'})
oldzip=ROOT/'packages/routine-unit-test-officecli/dist/ibm-bob-routine-unit-test-officecli-0.1.0.zip'
oldexpected=load(oldzip.parent/'checksums.json')['sha256']
assert sha(oldzip)==oldexpected
originals=['packages/routine-unit-test-officecli/skills/routine-unit-test-spec/assets/examples/alarm_unit_test.json',
           'packages/routine-unit-test-officecli/skills/routine-unit-test-spec/assets/templates/unit-test-spec-v01.docx',
           'packages/routine-unit-test-officecli/dist/ibm-bob-routine-unit-test-officecli-0.1.0.zip',
           'packages/routine-unit-test-officecli/dist/checksums.json']
p=subprocess.run(['git','diff','--quiet','--',*originals],capture_output=True)
assert p.returncode==0,'Legacy resources changed'
result={'status':'passed','utc':datetime.now(timezone.utc).isoformat(),'release_sha256':sha(SKILL/'release.json'),'jobs':summaries,
        'legacy_zip_sha256':sha(oldzip),'legacy_resources_git_unchanged':True,'old_logs_imported_as_pass':False,
        'bob_execution':'not_tested','all_page_visual_review':'not_performed','real_rtos_wcet':'not_verified',
        'note':'OfficeCLI/contract acceptance checks passed; specified C test/review items remain unexecuted.'}
save(OUT/'acceptance-summary.json',result)
print(json.dumps(result,ensure_ascii=False,indent=2))
