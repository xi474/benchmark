from pathlib import Path
from runtime import read
import subprocess
import sys
def run_candidate(root):
    subprocess.run([sys.executable,str(root/'run_all.py')],cwd=root,check=True)
    return read(root/'outputs/final_report.json')
root=Path(__file__).resolve().parent
report=run_candidate(root)
assert report['result']==read(root/'public_expected.json'),'Public example mismatch'
print('PUBLIC PASS')
