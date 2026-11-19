"""Maintainer-only example data; expectations authored from program contracts."""
from pathlib import Path
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[3]
SKILL=ROOT/'packages/routine-unit-test-officecli/skills/routine-unit-test-spec'
sys.path.insert(0,str(SKILL/'scripts'))
from _contract import required_refs, all_items
CODE=ROOT/'artifacts/routine-generic-validation/pipeline-code/range-clamp'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p,v): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def base(program, files, title):
 d=program['document']
 return {'schema_version':'0.2.0','document':{'id':'UTS-'+d['routine_id'],'title':title,'revision':'0.1','date':'2026-11-17',
         'status':d.get('status','draft'),'status_label':d.get('status_label',d.get('status','draft')),'routine_id':d['routine_id'],
         'routine_name':d['routine_name'],'template_id':'unit-test-spec-v02','author':'Codex; human review pending'},
         'target':{key:sha(files[role]) for key,role in [('program_spec_sha256','spec'),('source_sha256','source'),('header_sha256','header')]},
         'summary':'Expectations are derived from the supplied program specification. This document does not execute tests or import old pass results.',
         'environment':['Python 3.12 standard library; OfficeCLI 1.0.144 generates and structurally validates this document.','The C fixture is not executed by this workflow; platform and compiler validation are separate evidence.'],
         'assumptions':program.get('trial_assumptions',[]),'cases':[],'families':[],'static_checks':[],'coverage':[],'open_issues':program.get('open_issues',[])}
def named(**fields): return [{'name':k,'value':v} for k,v in fields.items()]
def coverage(data,program,caller=()):
 refs=required_refs(program)|{r for item in all_items(data) for r in item['spec_refs']}
 for ref in sorted(refs):
  items=[x for x in all_items(data) if ref in x['spec_refs']]
  if items:
   kinds={('review' if x in data['static_checks'] else 'test') for x in items}
   method='test_and_review' if len(kinds)>1 else next(iter(kinds))
   data['coverage'].append({'spec_ref':ref,'method':method,'item_ids':[x['id'] for x in items],
                            'rationale':'The listed unexecuted specification items address this exact source declaration.'})
  else:
   data['coverage'].append({'spec_ref':ref,'method':'caller' if ref in caller else 'unverified','item_ids':[],
                            'rationale':'Caller must satisfy ordered bounds.' if ref in caller else 'No executable or review evidence is claimed here. Further review of this source declaration is required.'})

out=SKILL/'assets/examples/range-clamp'
config=load(CODE/'job.json')
files={role:CODE/config[role] for role in ('spec','source','header')}
program=load(files['spec'])
out.mkdir(parents=True,exist_ok=True)
for role,name in [('spec','program-spec.json'),('source','RangeClamp.c'),('header','RangeClamp.h')]: (out/name).write_bytes(files[role].read_bytes())
data=base(program,files,'RangeClamp 単体テスト仕様書')
for case_id,title,refs,checks in [
 ('in-range-boundary','Within range and inclusive endpoints',['CLAMP-STEP-PRESERVE','CLAMP-EX-INSIDE'],[(2,-3,4,2),(-3,-3,4,-3),(4,-3,4,4)]),
 ('outside','Outside either bound',['CLAMP-STEP-LOWER','CLAMP-STEP-UPPER','CLAMP-EX-LOWER','CLAMP-EX-UPPER'],[(-8,-3,4,-3),(9,-3,4,4)]),
 ('equal-bounds','Equal lower and upper',['CLAMP-STEP-PRESERVE','CLAMP-EX-EQUAL'],[(7,7,7,7),(6,7,7,7),(8,7,7,7)])]:
 # Below/above equal bounds use the same source lower/upper rules.
 if case_id=='equal-bounds': refs+=['CLAMP-STEP-LOWER','CLAMP-STEP-UPPER']
 data['cases'].append({'id':case_id,'title':title,'purpose':'Check the source inclusive clamp rule independently of observed implementation output.',
     'spec_refs':refs,'initial_conditions':[],'steps':[{'id':'call-'+str(n),'action':'Call RangeClamp(value, lower, upper)',
     'inputs':named(value=v,lower=lo,upper=hi),'expected':[{'target':'return','comparison':'equals','value':expected}],
     'repeat':1,'note':'Expected result comes from the input program specification.'} for n,(v,lo,hi,expected) in enumerate(checks,1)],
     'judgment':'Every return equals the specification-derived expected int.'})
data['families']=[{'id':'small-domain','title':'Fixed inclusive bounds and five values','spec_refs':['CLAMP-STEP-LOWER','CLAMP-STEP-UPPER','CLAMP-STEP-PRESERVE'],
 'mode':'product','dimensions':[{'name':'value','values':[-8,-3,2,4,9]},{'name':'bounds','values':[{'lower':-3,'upper':4}]}],
 'sequence_length':0,'combination_count':5,'calls_per_instance':2,'call_count':10,
 'initial':'No state. Each instance supplies the listed ordered bounds.','enumeration':'Values in written order; each instance is called twice with identical arguments.',
 'method':'Compare both returns to the source rule independently; repeated calls also check absence of retained state.',
 'expected_rule':'For value < -3 expect -3; value > 4 expect 4; otherwise expect value. Both repeated calls must agree.',
 'examples':['value=-8 => -3 twice','value=2 => 2 twice','value=9 => 4 twice']}]
data['static_checks']=[{'id':'source-structure','title':'Bounded C90 arithmetic and state scope','spec_refs':['CLAMP-C90','CLAMP-OVERFLOW','/behavior/postconditions','/behavior/timing_semantics'],
 'method':'Read the exact locked source and header. Inspect comparisons, returns and declarations without deriving dynamic expected values from implementation.',
 'criterion':'No subtraction, overflow-producing arithmetic, loops, recursion, allocation, external calls or mutable static state.',
 'boundary':'Only the locked C/H function. This review item is unexecuted; real RTOS timing and WCET are outside the document-generation task.'}]
coverage(data,program,caller=['CLAMP-PRE-ORDER','/interface/preconditions'])
save(out/'unit-test-spec.json',data)

out=SKILL/'assets/examples/sample-hold'
out.mkdir(parents=True,exist_ok=True)
code=ROOT/'packages/routine-code-c90'
(out/'program-spec.json').write_bytes((ROOT/'packages/routine-spec-officecli/skills/routine-spec-doc/assets/examples/sample-hold/spec.json').read_bytes())
(out/'SampleHold_Update.c').write_bytes((code/'tests/fixture-implementations/SampleHold_Update.c').read_bytes())
(out/'SampleHold_Update.h').write_text('#ifndef SAMPLE_HOLD_UPDATE_H\n#define SAMPLE_HOLD_UPDATE_H\ntypedef struct { int last_sample; int has_sample; } SampleHoldState;\nint SampleHold_Update(SampleHoldState *state, int *out_sample);\n#endif\n',encoding='utf-8')
files={'spec':out/'program-spec.json','source':out/'SampleHold_Update.c','header':out/'SampleHold_Update.h'}
program=load(files['spec'])
data=base(program,files,'Synthetic SampleHold_Update 単体テスト仕様書')
data['environment']=[]
for case_id,status,sample,expstatus,expstate,expout in [('read-success',0,23,0,{'last_sample':23,'has_sample':1},23),('read-failure',7,-99,-2,{'last_sample':8,'has_sample':1},99)]:
 data['cases'].append({'id':case_id,'title':case_id,'purpose':'Check the supplied synthetic API success/failure contract.',
  'spec_refs':['SH-STEP-READ','SH-STEP-PRESERVE','SH-STEP-COMMIT', 'SH-EX-SUCCESS' if status==0 else 'SH-EX-FAILURE'],
  'initial_conditions':named(state={'last_sample':8,'has_sample':1},out_sample=99),
  'steps':[{'id':'mock-call','action':'Arrange supplied Project_ReadSample mock and call SampleHold_Update with valid disjoint storage.',
   'inputs':named(api_status=status,api_sample=sample),
   'expected':[{'target':'return','comparison':'equals','value':expstatus},{'target':'state','comparison':'equals','value':expstate},
               {'target':'out_sample','comparison':'equals','value':expout},{'target':'api_call_count','comparison':'equals','value':1}],
   'repeat':1,'note':'Synthetic test fixture only; no real RTOS or device API is inferred.'}],
  'judgment':'All return, state, output, and call-count comparisons match the supplied API specification.'})
data['static_checks']=[{'id':'fixture-boundary','title':'Fixture-only API boundary','spec_refs':['SH-C-SUPPLIED','SH-C-RESOURCES','SH-STEP-POINTERS'],
 'method':'Review exact locked source and supplied synthetic API contract; follow null checks before the API call.',
 'criterion':'No API call/write before pointer validation; only the supplied immediate API contract; no invented ABI, allocation, loops or shared mutable state.',
 'boundary':'Synthetic interface only. External API synchronization, real target timing and physical input behavior are not verified.'}]
coverage(data,program)
save(out/'unit-test-spec.json',data)
print(json.dumps({'status':'examples-authored','range_cases':3,'range_family_calls':10,'sample_cases':2,'sample_families':0}))

# Separate v02 migration data; the original v01 sample and ZIP remain unchanged.
old=load(SKILL/'assets/examples/alarm_unit_test.json')
legacy=ROOT/'prototypes/routine-code-poc'
config=load(legacy/'job.json')
files={role:legacy/config[role] for role in ('spec','source','header')}
program=load(files['spec'])
out=SKILL/'assets/examples/alarm-regression';out.mkdir(parents=True,exist_ok=True)
for role,name in [('spec','program-spec.json'),('source','AlarmQualification.c'),('header','AlarmQualification.h')]: (out/name).write_bytes(files[role].read_bytes())
data=base(program,files,old['document']['title'])
data['document'].update({key:val for key,val in old['document'].items() if key not in ('template_id',)})
data['document']['template_id']='unit-test-spec-v02'
data['summary']=old['summary']
data['environment']=old['environment']
for case in old['cases']:
 current={key:val for key,val in case.items() if key not in ('initial','steps')}
 current['initial_conditions']=[{'name':initial['instance'], 'value':{key:val for key,val in initial.items() if key!='instance'}} for initial in case['initial']]
 current['steps']=[]
 for step in case['steps']:
  current['steps'].append({'id':step['id'],'action':'Call '+program['document']['routine_name']+' for instance '+step['instance'],
    'inputs':[{'name':key,'value':val} for key,val in step.items() if key not in ('id','expected','repeat','note')],
    'expected':[{'target':key,'comparison':'equals' if val!='preserve' else 'unchanged','value':val} for key,val in step['expected'].items()],
    'repeat':step['repeat'],'note':step['note']})
 data['cases'].append(current)
data['families']=[{**family,'calls_per_instance':family['call_count']//family['combination_count']} for family in old['families']]
data['static_checks']=old['static_checks']
coverage(data,program,caller=['CON-04','/interface/preconditions'])
# Keep original allocation rationale where the migrated row uses the same ref.
old_rows={row['spec_ref']:row for row in old['coverage']}
for row in data['coverage']:
 if row['spec_ref'] in old_rows: row['rationale']=old_rows[row['spec_ref']]['rationale']
save(out/'unit-test-spec.json',data)
print(json.dumps({'alarm_migrated_cases':len(data['cases']),'families':len(data['families']),'original_sample_unchanged':True}))
