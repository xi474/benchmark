from pathlib import Path
from runtime import execute,read
root=Path(__file__).resolve().parent
report=execute(root)
assert report['result']==read(root/'public_expected.json'),'Public example mismatch'
print('PUBLIC PASS')
