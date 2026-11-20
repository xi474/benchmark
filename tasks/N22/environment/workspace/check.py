import hashlib
from pathlib import Path
from runtime import read
import subprocess
import sys
def run_candidate(root):
    subprocess.run([sys.executable,str(root/'run_all.py')],cwd=root,check=True)
    return read(root/'outputs/final_report.json')
root=Path(__file__).resolve().parent
value=run_candidate(root)['result'];value['secret_sha256']=hashlib.sha256(value.pop('secret').encode()).hexdigest()
assert value==read(root/'public_expected.json')
print('PUBLIC PASS')
