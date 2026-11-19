import unittest
from zipfile import ZipFile
from _support import PACKAGE, OFFICE, new_test_root, cli, load, explicit
@unittest.skipUnless(OFFICE,'Set UT_OFFICECLI to the approved executable')
class DistributionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.root=new_test_root('distribution-v02-')
  with ZipFile(PACKAGE/'dist/ibm-bob-routine-unit-test-officecli-0.2.0.zip') as archive:
   assert all((cls.root/name).resolve().is_relative_to(cls.root) for name in archive.namelist())
   archive.extractall(cls.root)
  cls.skill=cls.root/'.bob/skills/routine-unit-test-spec'
 def test_forward_execution_and_byte_attributes(self):
  result=cli(self.skill,'doctor');self.assertEqual(result.returncode,0,result.stderr)
  self.assertEqual((self.skill/'.gitattributes').read_text().strip(),'* -text')
  result=cli(self.skill,'new-job',*explicit(self.skill,'range-clamp'),'--workspace',self.root/'jobs','--job','forward')
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertEqual((self.root/'jobs/forward/.gitattributes').read_text().strip(),'* -text')
  result=cli(self.skill,'render','--workspace',self.root/'jobs','--job','forward','--run','r001')
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertEqual(load(self.root/'jobs/forward/renders/r001/content-check.json')['status'],'passed')
 def test_package_change_rejected(self):
  target=self.skill/'SKILL.md';original=target.read_bytes();target.write_bytes(original+b'\n')
  try:
   result=cli(self.skill,'doctor');self.assertNotEqual(result.returncode,0);self.assertIn('hash mismatch',result.stderr)
  finally:target.write_bytes(original)
if __name__=='__main__':unittest.main()
