import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def contracts():
    return sorted(p for p in ROOT.rglob('contract.json') if 'outputs' not in p.relative_to(ROOT).parts)
def write(path,data):
    p=ROOT/path; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def main():
    domain_mode=len(sys.argv)>1 and sys.argv[1]=='domains'
    selected=[p for p in contracts() if not domain_mode or p.parent.parent.name=='domains']
    if not selected: raise ValueError('no component contracts')
    values={}
    for p in selected:
        c=json.loads(p.read_text(encoding='utf-8'))
        value=json.loads((ROOT/c['output']).read_text(encoding='utf-8'))
        if value['name']!=c['name']: raise ValueError('component mismatch')
        values[c['name']]=value['result']
    if domain_mode:
        records={}
        for result in values.values():
            for r in result['records']:
                key=(r['source'],r['id'])
                if key in records and records[key]!=r: raise ValueError('source/id conflict')
                records[key]=r
        write('outputs/domain_core.json',{'name':'domain_core','result':{'records':sorted(records.values(),key=lambda r:(r['source'],r['id']))}})
    else: write('outputs/core_manifest.json',{'components':dict(sorted(values.items()))})
if __name__=='__main__': main()
