"""Public scaffold and QA-only complete infrastructure implementations."""
MODEL='''import json, math
from pathlib import Path

def load_payload(path):
    def finite(v):
        if isinstance(v,float) and not math.isfinite(v): raise ValueError('nonfinite JSON')
        if isinstance(v,dict):
            for x in v.values(): finite(x)
        if isinstance(v,list):
            for x in v: finite(x)
    try: data=json.loads(Path(path).read_text(encoding='utf-8'))
    except (ValueError,UnicodeError) as e: raise ValueError('invalid JSON') from e
    if type(data) not in (dict,list): raise ValueError('JSON object/array required')
    finite(data)
    return data
'''
RENDER='''import json
from pathlib import Path
from model import load_payload
from transform import transform
ROOT=Path(__file__).resolve().parents[DEPTH]

def build_component(root,contract_path):
    root=Path(root); c=load_payload(Path(contract_path))
    return transform([load_payload(root/p) for p in c['inputs']],c)

if __name__=='__main__':
    cp=Path(__file__).with_name('contract.json'); c=load_payload(cp)
    value=build_component(ROOT,cp); out=ROOT/c['output']; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\\n',encoding='utf-8')
'''
CHECK_MODULE='''import copy, importlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[DEPTH]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(Path(__file__).resolve().parent))
from model import load_payload
from transform import transform
from render import build_component

def main():
    cp=Path(__file__).with_name('contract.json'); c=load_payload(cp)
    payloads=[load_payload(ROOT/p) for p in c['inputs']]; before=copy.deepcopy(payloads); cc=copy.deepcopy(c)
    result=transform(payloads,c)
    assert payloads==before and c==cc,'inputs/contract mutated'
    assert type(result) is dict and set(result)=={'name','result'} and result['name']==c['name'] and type(result['result']) is dict
    assert build_component(ROOT,cp)==result
    assert json.loads((ROOT/c['output']).read_text(encoding='utf-8'))==result
    PACKAGE_CHECK
    print('MODULE_OK',c['name'])
if __name__=='__main__': main()
'''
INTEGRATE='''import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
    components={}
    for cp in sorted(ROOT.rglob('contract.json')):
        if 'outputs' in cp.relative_to(ROOT).parts: continue
        c=json.loads(cp.read_text(encoding='utf-8')); v=json.loads((ROOT/c['output']).read_text(encoding='utf-8'))
        if set(v)!={'name','result'} or v['name']!=c['name'] or c['name'] in components: raise ValueError('bad component')
        components[c['name']]=v['result']
    if not components: raise ValueError('no contracts')
    out=ROOT/'outputs/core_manifest.json'; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'components':components},ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\\n',encoding='utf-8')
if __name__=='__main__': main()
'''
CHECK='''import json, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    out=ROOT/'outputs'
    if out.is_symlink() or out.resolve().parent!=ROOT: raise ValueError('unsafe outputs')
    if out.exists(): shutil.rmtree(out)
    if (ROOT/'materialize.py').is_file(): subprocess.run([sys.executable,str(ROOT/'materialize.py')],cwd=ROOT,check=True,timeout=30)
    subprocess.run([sys.executable,str(ROOT/'run_all.py')],cwd=ROOT,check=True,timeout=180)
    contracts=[x for x in ROOT.rglob('contract.json') if 'outputs' not in x.relative_to(ROOT).parts]
    assert contracts,'no contracts'
    for cp in contracts: subprocess.run([sys.executable,str(cp.with_name('check_module.py'))],cwd=ROOT,check=True,timeout=30)
    core=json.loads((out/'core_manifest.json').read_text(encoding='utf-8')); report=json.loads((out/'final_report.json').read_text(encoding='utf-8'))
    assert set(core)=={'components'} and len(core['components'])==len(contracts)
    assert set(report)=={'title','component_count','sha256','attention'} and report['component_count']==len(contracts) and len(report['sha256'])==64
    print('LOCAL_CHECKS_PASSED; external verifier determines official correctness')
if __name__=='__main__': main()
'''
RUN_ALL='''import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
    if (ROOT/'materialize.py').is_file():subprocess.run([sys.executable,str(ROOT/'materialize.py')],cwd=ROOT,check=True)
    pending=[p for p in ROOT.rglob('contract.json') if 'outputs' not in p.relative_to(ROOT).parts]
    done=set()
    # Only outputs produced by this invocation satisfy a dependency.
    while pending:
        progress=False
        for cp in pending[:]:
            c=json.loads(cp.read_text(encoding='utf-8'))
            if not all((ROOT/x).is_file() and (not x.startswith('outputs/') or x in done) for x in c['inputs']):continue
            subprocess.run([sys.executable,str(cp.with_name('render.py'))],cwd=ROOT,check=True,timeout=30)
            done.add(c['output']);pending.remove(cp);progress=True
        if not progress:raise ValueError('missing dependency or cyclic contracts')
    subprocess.run([sys.executable,str(ROOT/'integrate.py')],cwd=ROOT,check=True)
    subprocess.run([sys.executable,str(ROOT/'final_report.py')],cwd=ROOT,check=True)
if __name__=='__main__':main()
'''
FINAL='''import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TITLE=TITLE_LITERAL
def main():
    core=json.loads((ROOT/'outputs/core_manifest.json').read_text(encoding='utf-8')); attention=[]
    for name,r in core['components'].items():
        if r.get('blocked') is True or any(r.get(k) is False for k in ['complete','checkout','committed','ok']) or any(bool(r.get(k)) for k in ['unavailable','missing','conflicts','unreachable']):attention.append(name)
    report=dict(title=TITLE,component_count=len(core['components']),sha256=hashlib.sha256(json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),attention=sorted(attention))
    (ROOT/'outputs/final_report.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\\n',encoding='utf-8')
if __name__=='__main__':main()
'''
