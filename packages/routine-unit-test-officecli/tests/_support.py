import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]
SKILL = PACKAGE / 'skills/routine-unit-test-spec'
WORKSPACE = PACKAGE.parents[1]
OFFICE = os.environ.get('UT_OFFICECLI')
CODE_JOB = WORKSPACE / 'prototypes/routine-code-poc'


def new_test_root(prefix):
    parent = WORKSPACE / 'artifacts/routine-unit-test-officecli/verification'
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=parent)).resolve()


def cli(skill, *args):
    return subprocess.run([sys.executable, '-X', 'utf8', '-S', '-B',
                           str(skill / 'scripts/utflow.py'), *map(str, args),
                           '--officecli', OFFICE], capture_output=True, text=True,
                          encoding='utf-8', timeout=180, shell=False)


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
