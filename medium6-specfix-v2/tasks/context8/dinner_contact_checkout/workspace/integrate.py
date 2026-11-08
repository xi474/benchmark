import json
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
    out.write_text(json.dumps({'components':components},ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')
if __name__=='__main__': main()
