"""Trusted external verifier. Mount separately from the candidate workspace."""
from __future__ import annotations
import argparse, copy, hashlib, json, math, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'_authoring'))
from reference import TASKS,canonical,evaluate
from vectors import available,cases_for

def same(a,b):
    if type(a) in (int,float) and type(b) in (int,float):return math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-9)
    if type(a) is not type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b
def dump(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
def report(core,title):
    attention=[]
    for name,r in core['components'].items():
        if r.get('blocked') is True or any(r.get(k) is False for k in ['complete','checkout','committed','ok']) or any(bool(r.get(k)) for k in ['unavailable','missing','conflicts','unreachable']):attention.append(name)
    return dict(title=title,component_count=len(core['components']),sha256=hashlib.sha256(canonical(core).encode()).hexdigest(),attention=sorted(attention))
def integrity(w,seal,post=False):
    for rel,expected in {**seal['initial'],**(seal['generated'] if post else {})}.items():
        path=w/rel
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise AssertionError('protected file changed: '+rel)
        if w not in path.resolve().parents:raise AssertionError('protected path escaped: '+rel)
    if not post:
        for rel,expected in seal['generated'].items():
            if (w/rel).exists():
                path=w/rel
                if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise AssertionError('generated file changed: '+rel)
def probe(w,t,only=None):
    count=0; loaders=0
    for folder,c in t['components']:
        if only and c['name']!=only:continue
        cases=cases_for(t,c); expected=[]
        for case in cases:
            try:expected.append(dict(kind='value',value=evaluate(case['payloads'],case['contract'])))
            except ValueError:expected.append(dict(kind='ValueError'))
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('probe.py')),str(w),folder,t['style']],input=json.dumps(dict(cases=cases),ensure_ascii=False),capture_output=True,text=True,encoding='utf-8',timeout=45,cwd=w)
        if result.returncode:raise AssertionError('API process failed '+folder+': '+result.stderr[-1500:])
        try:actual=json.loads(result.stdout)
        except ValueError as exc:raise AssertionError('API output invalid '+folder+': '+result.stdout[-1000:]) from exc
        if not all(actual['model_cases']) or not actual['render_ok']:raise AssertionError('loader/render probe failed '+folder)
        if len(actual['responses'])!=len(expected):raise AssertionError('API response count '+folder)
        for case,got,wanted in zip(cases,actual['responses'],expected):
            if not same(got,wanted):raise AssertionError('held-out API mismatch: '+folder+' '+case['label'])
        count+=len(cases);loaders+=len(actual['model_cases'])+1
    return dict(api_cases=count,loader_render_cases=loaders)
def verify(entry,workspace,api=True):
    t=next((t for t in TASKS if t['style']+'/'+t['slug']==entry),None)
    if t is None:raise ValueError('unknown entry')
    w=Path(workspace).resolve();seals=json.loads((ROOT/'verifier/protected_hashes.json').read_text(encoding='utf-8'));seal=seals[entry];integrity(w,seal)
    result=subprocess.run([sys.executable,str(w/'check.py')],cwd=w,capture_output=True,text=True,encoding='utf-8',timeout=240)
    integrity(w,seal,post=t['style']=='linux2')
    if result.returncode:raise AssertionError('local execution failed: '+result.stdout[-500:]+' '+result.stderr[-1600:])
    values=available(t,t['fixture'](47));expected={c['output']:values[c['output']] for _,c in t['components']};core={'components':{c['name']:expected[c['output']]['result'] for _,c in t['components']}};expected['outputs/core_manifest.json']=core
    for rel,wanted in expected.items():
        path=w/rel
        if path.is_symlink() or not path.is_file() or w not in path.resolve().parents:raise AssertionError('missing/unsafe output '+rel)
        source=path.read_text(encoding='utf-8');actual=json.loads(source)
        if not same(actual,wanted):raise AssertionError('wrong output '+rel)
        if source!=dump(actual):raise AssertionError('noncanonical JSON '+rel)
    core_actual=json.loads((w/'outputs/core_manifest.json').read_text(encoding='utf-8'));wanted=report(core_actual,t['title']);path=w/'outputs/final_report.json';source=path.read_text(encoding='utf-8');actual=json.loads(source)
    if actual!=wanted or source!=dump(actual):raise AssertionError('wrong final report')
    stats=probe(w,t) if api else dict(api_cases=0,loader_render_cases=0)
    integrity(w,seal,post=True)
    return dict(entry=entry,id=t['id'],status='passed',scope='core_only',output_count=len(expected)+1,**stats)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--entry',required=True);parser.add_argument('--workspace',required=True);args=parser.parse_args()
    try:result=verify(args.entry,args.workspace)
    except Exception as exc:print(json.dumps(dict(status='failed',reason=str(exc)),ensure_ascii=False));return 1
    print(json.dumps(result,ensure_ascii=False));return 0
if __name__=='__main__':sys.exit(main())
