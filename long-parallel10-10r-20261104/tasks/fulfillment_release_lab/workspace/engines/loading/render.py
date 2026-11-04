import importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name):
    sys.path.insert(0,str(ROOT));return __import__('engines.'+HERE.name+'.'+name,fromlist=[name])
def build():
    c=json.loads((HERE/'contract.json').read_text());p=json.loads((ROOT/c['inputs'][0]).read_text())
    n=load('model').normalize(p);r=load('solver').solve(n,c)
    assert load('audit').verify(p,r,c) is True,'result audit rejected'
    out=ROOT/c['output'];out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(dict(name=HERE.name,result=r),sort_keys=True,allow_nan=False,indent=2)+'\n');return r
if __name__=='__main__':build()
