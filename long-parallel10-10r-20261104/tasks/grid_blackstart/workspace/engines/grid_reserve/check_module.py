import copy,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
def load(name):
    sys.path.insert(0,str(HERE.parents[1]));return __import__('engines.'+HERE.name+'.'+name,fromlist=[name])
def stable(x):return json.dumps(x,sort_keys=True,allow_nan=False)
def main():
    a,b,v=load('model'),load('solver'),load('audit');c=json.loads((HERE/'contract.json').read_text());fs=json.loads((HERE/'fixtures.json').read_text())
    for i,row in enumerate(fs):
        p=copy.deepcopy(row['input']);before=copy.deepcopy(p);cb=copy.deepcopy(c)
        n=a.normalize(p);assert stable(n)==stable(row['normalized']),('normalize',i)
        assert stable(a.normalize(n))==stable(n),('idempotence',i)
        r=b.solve(p,c);assert stable(r)==stable(row['expected']),('solve',i,r,row['expected'])
        rb=copy.deepcopy(r);assert v.verify(p,r,c) is True,('audit_correct',i)
        for bad in [None,{},dict(r,unexpected=True)]:assert v.verify(p,bad,c) is False,('audit_invalid',i)
        assert p==before and c==cb and r==rb,'mutated arguments'
    for p in [None,True,[],{},'bad',3]:
        for f in [lambda:a.normalize(p),lambda:b.solve(p,c),lambda:v.verify(p,{},c)]:
            try:f()
            except ValueError:pass
            else:raise AssertionError('invalid input accepted')
    load('render').build();print('FOCUSED_CHECK_PASS '+HERE.name+' '+str(len(fs)))
if __name__=='__main__':main()
