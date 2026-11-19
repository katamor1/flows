import copy
import hashlib
import shutil
import unittest
from pathlib import Path
from _support import SKILL, OFFICE, CODE_JOB, WORKSPACE, new_test_root, cli, load, save, explicit

@unittest.skipUnless(OFFICE,'Set UT_OFFICECLI to the approved executable')
class RenderTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.root=new_test_root('render-v02-')
  for name in ('range-clamp','sample-hold'):
   result=cli(SKILL,'new-job',*explicit(SKILL,name),'--workspace',cls.root,'--job',name)
   if result.returncode: raise RuntimeError(result.stderr)
 def command(self,name,*args): return cli(SKILL,*args,'--workspace',self.root,'--job',name)
 def test_real_non_alarm_variable_documents_and_repeat(self):
  semantics=[]
  for name,expected_cases,expected_families in [('range-clamp',3,1),('sample-hold',2,0)]:
   for run in ('r001','r002') if name=='range-clamp' else ('r001',):
    result=self.command(name,'render','--run',run)
    self.assertEqual(result.returncode,0,result.stderr)
    folder=self.root/name/'renders'/run
    check=load(folder/'content-check.json');self.assertEqual(check['status'],'passed')
    self.assertEqual(check['template_content_and_formatting'],'matched')
    trace=load(folder/'traceability.json')
    self.assertEqual(trace['counts']['representative_cases'],expected_cases)
    self.assertEqual(trace['counts']['parameter_families'],expected_families)
    self.assertTrue(all(x['status']=='not_executed' and x['evidence']==[] for x in load(folder/'execution-record.json')['results']))
    if name=='range-clamp': semantics.append(check['semantic_sha256'])
  self.assertEqual(*semantics)
  result=self.command('range-clamp','render','--run','r001');self.assertNotEqual(result.returncode,0)
 def test_source_and_lock_tamper_rejected_without_publishing(self):
  job=self.root/'range-clamp';lock=load(job/'input-lock.json')
  for path in (job/lock['bindings']['source'],job/'input-lock.json'):
   original=path.read_bytes();path.write_bytes(original+b'\n')
   try:
    result=self.command('range-clamp','render','--run','tampered')
    self.assertNotEqual(result.returncode,0);self.assertFalse((job/'renders/tampered').exists())
   finally: path.write_bytes(original)
 def test_invalid_expected_and_legacy_pass_rejected(self):
  job=self.root/'range-clamp'
  for relative,mutator in [('source/unit-test-spec.json',lambda d:d['cases'][0]['steps'][0].update(expected=[])),
                           ('records/execution-record.json',lambda d:d['results'][0].update(status='passed',evidence=['old aggregate log']))]:
   path=job/relative;original=path.read_bytes();data=load(path);mutator(data);save(path,data)
   try:
    result=self.command('range-clamp','render','--run','invalid');self.assertNotEqual(result.returncode,0)
    self.assertFalse((job/'renders/invalid').exists())
   finally: path.write_bytes(original)
 def test_blank_skeleton_rejected(self):
  args=explicit(SKILL,'range-clamp')[:-2]
  result=cli(SKILL,'new-job',*args,'--workspace',self.root,'--job','blank')
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertTrue(load(self.root/'blank/source/unit-test-spec.json')['cases']==[])
  result=self.command('blank','validate');self.assertNotEqual(result.returncode,0)
 def test_generic_and_legacy_code_jobs(self):
  sample=SKILL/'assets/examples/range-clamp/unit-test-spec.json'
  result=cli(SKILL,'new-job','--code-job',CODE_JOB,'--unit-test-spec',sample,'--workspace',self.root,'--job','generic-code')
  self.assertEqual(result.returncode,0,result.stderr)
  result=self.command('generic-code','validate');self.assertEqual(result.returncode,0,result.stderr)
  result=cli(SKILL,'new-job','--code-job',WORKSPACE/'prototypes/routine-code-poc','--unit-test-spec',SKILL/'assets/examples/alarm-regression/unit-test-spec.json','--workspace',self.root,'--job','legacy-code')
  self.assertEqual(result.returncode,0,result.stderr)
  result=self.command('legacy-code','validate');self.assertEqual(result.returncode,0,result.stderr)
 def test_generation_hash_and_additional_asset_tamper_rejected(self):
  origin=self.root/'codecopy';shutil.copytree(CODE_JOB,origin)
  config=load(origin/'job.json');record=load(origin/config['generation_record'])
  candidates=[name for name in record['file_hashes'] if name not in (config['spec'],config['source'],config['header'])]
  self.assertTrue(candidates)
  (origin/candidates[0]).write_bytes((origin/candidates[0]).read_bytes()+b'\n')
  result=cli(SKILL,'new-job','--code-job',origin,'--unit-test-spec',SKILL/'assets/examples/range-clamp/unit-test-spec.json','--workspace',self.root,'--job','bad-assets')
  self.assertNotEqual(result.returncode,0);self.assertIn('hash mismatch',result.stderr)
  self.assertFalse((self.root/'bad-assets').exists())

if __name__=='__main__':unittest.main()
