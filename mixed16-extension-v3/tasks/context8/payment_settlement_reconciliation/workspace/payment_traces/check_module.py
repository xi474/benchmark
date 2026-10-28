import json,sys,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from model import load_payload
from transform import transform
from render import build_component
C=json.loads(Path(__file__).with_name('contract.json').read_text(encoding='utf-8'))
payloads=[load_payload(ROOT/p) for p in C['inputs']]
before=copy.deepcopy(payloads)
result=transform(payloads,C)
assert payloads==before, 'must not mutate inputs'
assert isinstance(result,dict) and set(result)=={'name','result'}
assert result['name']==C['name'] and isinstance(result['result'],dict)
assert build_component(ROOT,Path(__file__).with_name('contract.json'))==result
out=json.loads((ROOT/C['output']).read_text(encoding='utf-8'))
assert out==result, 'output must match function result'
print('MODULE_OK',C['name'])
