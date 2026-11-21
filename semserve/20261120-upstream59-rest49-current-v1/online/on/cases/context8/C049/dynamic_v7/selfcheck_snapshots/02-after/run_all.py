import argparse,json
from pathlib import Path
import solution

p=argparse.ArgumentParser()
p.add_argument('--check',action='store_true')
p.add_argument('--input',default='public_input.json')
p.add_argument('--output',default='output.json')
a=p.parse_args()
if a.check:
    value=json.loads(Path('public_input.json').read_text(encoding='utf-8'))
    expected=json.loads(Path('public_expected.json').read_text(encoding='utf-8'))
    actual=solution.transform(value)
    def eq(x,y):
        if isinstance(x,(int,float)) and isinstance(y,(int,float)):
            return abs(x-y)<=1e-8+1e-8*abs(y)
        if isinstance(x,list) and isinstance(y,list):return len(x)==len(y) and all(eq(a,b) for a,b in zip(x,y))
        if isinstance(x,dict) and isinstance(y,dict):return x.keys()==y.keys() and all(eq(x[k],y[k]) for k in x)
        return x==y
    assert eq(actual,expected)
    print('public check passed')
else:
    solution.build_component(a.input,a.output)
