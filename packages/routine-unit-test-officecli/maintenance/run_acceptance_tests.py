from pathlib import Path
from datetime import datetime, timezone
import json, os, subprocess, sys, time
out=Path('artifacts/routine-generic-validation/unit-tests')
command=[sys.executable,'-X','utf8','-S','-B','-m','unittest','discover','-s','packages/routine-unit-test-officecli/tests','-v']
env={**os.environ,'UT_OFFICECLI':r'C:/Users/stell/AppData/Local/Programs/IBM Bob/resources/app/extensions/bob-code/dist/officecli.exe'}
start=time.monotonic();p=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',env=env)
(out/'unittest.stdout.txt').write_text(p.stdout,encoding='utf-8');(out/'unittest.stderr.txt').write_text(p.stderr,encoding='utf-8')
result={'command':command,'exit_code':p.returncode,'elapsed_seconds':round(time.monotonic()-start,3),'utc':datetime.now(timezone.utc).isoformat(),
        'stdout':'unittest.stdout.txt','stderr':'unittest.stderr.txt','bob_executed':False,'all_page_visual_review':'not_performed'}
(out/'unittest-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(p.stderr);print(json.dumps(result));sys.exit(p.returncode)
