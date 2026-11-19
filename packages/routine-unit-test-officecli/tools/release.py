"""Maintainer-only release sealing and deterministic IBM Bob ZIP packaging."""
from pathlib import Path
import argparse
import hashlib
import json
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'skills/routine-unit-test-spec'
VERSION='0.2.0'
def sha(b): return hashlib.sha256(b).hexdigest()
def resources(): return sorted(p.relative_to(SKILL).as_posix() for p in SKILL.rglob('*') if p.is_file() and p.name!='release.json')
def seal():
 files=resources()
 if any('__pycache__' in name for name in files): raise ValueError('Unexpected bytecode')
 release={'name':'routine-unit-test-officecli','version':VERSION,'profile_id':'generic-unit-test-v02',
          'template_id':'unit-test-spec-v02','template_revision':VERSION,'schema':'assets/schema/unit-test-spec.schema.json',
          'example':'assets/examples/range-clamp/unit-test-spec.json','template':'assets/templates/unit-test-spec-v02.docx',
          'officecli':{'version':'1.0.144','sha256':'eec03daa7978a1e8f28a4ee0ce910ef9e3cb355d26a7fa4afcecadfe34693fbb'},
          'limits':['Project-specific hashes; code job0.1.0/0.2.0 or explicit project inputs','Python 3.12 standard library',
                    'All test/review items remain not_executed','Visual/Bob/RTOS/WCET/requirements approval are separate checks'],
          'files':{name:sha((SKILL/name).read_bytes()) for name in files}}
 (SKILL/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':'sealed','release_sha256':sha((SKILL/'release.json').read_bytes())}))
def bundle():
 release_bytes=(SKILL/'release.json').read_bytes();release=json.loads(release_bytes)
 if set(resources())!=set(release['files']): raise ValueError('Resource inventory mismatch')
 payload={}
 for name,expected in release['files'].items():
  content=(SKILL/name).read_bytes()
  if sha(content)!=expected: raise ValueError('Unsealed resource: '+name)
  payload['.bob/skills/routine-unit-test-spec/'+name]=content
 payload['.bob/skills/routine-unit-test-spec/release.json']=release_bytes
 payload['.bob/rules/30-routine-unit-test-spec.md']=(ROOT/'content/30-routine-unit-test-spec.md').read_bytes()
 payload['BOB-TEAM-README.md']=(ROOT/'README.md').read_bytes()
 meta={'name':release['name'],'version':VERSION,'generator_backend':'OfficeCLI','python_dependencies':'standard library only',
       'release_sha256':sha(release_bytes),'pinned_officecli':release['officecli'],'bob_chat_skill_activation':'not_tested',
       'test_execution':'not_executed','files':{name:sha(b) for name,b in sorted(payload.items())}}
 payload['distribution.json']=(json.dumps(meta,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
 target=ROOT/'dist'/f'ibm-bob-routine-unit-test-officecli-{VERSION}.zip'
 with ZipFile(target,'w',compression=ZIP_DEFLATED,compresslevel=9) as archive:
  for name,content in sorted(payload.items()):
   item=ZipInfo(name,(2000,1,1,0,0,0));item.compress_type=ZIP_DEFLATED;item.external_attr=0o644<<16
   archive.writestr(item,content)
 record={'file':target.name,'sha256':sha(target.read_bytes()),'bytes':target.stat().st_size,'files':len(payload),'release_sha256':sha(release_bytes)}
 (target.parent/('checksums-'+VERSION+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(record))
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['seal','bundle']);args=parser.parse_args()
 seal() if args.command=='seal' else bundle()
