import json
from pathlib import Path
from solution import transform
from math import isfinite
p=json.loads(Path('public_input.json').read_text(encoding='utf-8'))
expected=json.loads(Path('public_expected.json').read_text(encoding='utf-8'))
contract=json.loads(Path('contract.json').read_text(encoding='utf-8'))
tol=contract.get('numeric_tolerance',0) or 0
def equal(a,b):
 if isinstance(a,bool) or isinstance(b,bool):return type(a)==type(b) and a==b
 if isinstance(a,(int,float)) and isinstance(b,(int,float)):
  atol=tol.get('atol',0) if isinstance(tol,dict) else tol
  rtol=tol.get('rtol',0) if isinstance(tol,dict) else 0
  return isfinite(a) and isfinite(b) and abs(a-b)<=atol+rtol*abs(b)
 if isinstance(a,dict) and isinstance(b,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
 if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
 return type(a)==type(b) and a==b
assert equal(transform(p),expected)
print('public check passed')
