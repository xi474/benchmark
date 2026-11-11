import hashlib
from pathlib import Path
from runtime import execute,read
root=Path(__file__).resolve().parent
value=execute(root)['result'];value['secret_sha256']=hashlib.sha256(value.pop('secret').encode()).hexdigest()
assert value==read(root/'public_expected.json')
print('PUBLIC PASS')
