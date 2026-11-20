"""No model calls. Fresh reference/blank/tampered workspaces stay outside task sources."""
import argparse,concurrent.futures,hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
from arithmetic import reward
HERE=Path(__file__).resolve().parent
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8',newline='\n')
def load(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
HARD_RUN='''import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def run(path,*args):subprocess.run([sys.executable,str(path),*args],cwd=ROOT,check=True)
if (ROOT/'materialize.py').is_file():run(ROOT/'materialize.py')
contracts=[(p,json.loads(p.read_text(encoding='utf-8'))) for p in ROOT.rglob('contract.json')]
pending=contracts[:];done=set()
while pending:
    progress=False
    if any('outputs/domain_core.json' in c['inputs'] for _,c in pending) and 'outputs/domain_core.json' not in done:
        domains=[c for p,c in contracts if p.parent.parent.name=='domains']
        if domains and all(c['output'] in done for c in domains):run(ROOT/'integrate.py','domains');done.add('outputs/domain_core.json');progress=True
    for p,c in pending[:]:
        if all((ROOT/x).is_file() and (not x.startswith('outputs/') or x in done) for x in c['inputs']):run(p.with_name('render.py'));done.add(c['output']);pending.remove((p,c));progress=True
    if not progress:raise ValueError('unresolved contracts')
run(ROOT/'integrate.py');run(ROOT/'final_report.py')
'''
SDK={
'config/coerce.py':'''def coerce_like(v,e):
    if type(e) is bool:
        if type(v) is bool:return v
        if str(v).lower() in ('true','1','yes','on'):return True
        if str(v).lower() in ('false','0','no','off'):return False
        raise ValueError('bad bool')
    if type(e) is int:return int(v)
    if type(e) is float:return float(v)
    if type(e) is str:return str(v)
    return v
''',
'config/merge.py':'''import copy
def deep_merge(a,b):
    out=copy.deepcopy(a)
    for k,v in b.items():out[k]=deep_merge(out[k],v) if isinstance(out.get(k),dict) and isinstance(v,dict) else copy.deepcopy(v)
    return out
''',
'config/loader.py':'''from config.merge import deep_merge
from config.coerce import coerce_like
def load_config(defaults,file_data,env,overrides):
    out=deep_merge(defaults,file_data)
    for k,v in env.items():
        if not k.startswith('SDK_'):continue
        keys=k[4:].lower().split('__');dest=out
        for key in keys[:-1]:dest=dest.setdefault(key,{})
        dest[keys[-1]]=coerce_like(v,dest.get(keys[-1],v))
    def merge(a,b):
        for k,v in b.items():
            if isinstance(a.get(k),dict) and isinstance(v,dict):merge(a[k],v)
            else:a[k]=coerce_like(v,a.get(k,v))
    merge(out,overrides);return out
''',
'cli/names.py':'''def canonical_name(name):
    return {'--timeout':'request_timeout','--request-timeout':'request_timeout','--retries':'retries','--no-verify':'verify'}.get(name,name.lstrip('-').replace('-','_'))
''',
'cli/values.py':'''def canonical_value(name,value):
    if name in ('request_timeout','retries'):return int(value)
    if name=='verify':return not bool(value)
    return value
''',
'cli/adapter.py':'''from cli.names import canonical_name
from cli.values import canonical_value
def adapt_args(source):
    out={}
    for k,v in source.items():
        name=canonical_name(k);value=canonical_value(name,v)
        if name in out and out[name]!=value:raise ValueError('alias conflict')
        out[name]=value
    return out
''',
'reports/upgrade.py':'''import copy
def upgrade_record(row):
    known={'id','name','status','ok','duration_ms','elapsed','extensions'}
    extensions=copy.deepcopy(row.get('extensions',{}));extensions.update({k:copy.deepcopy(v) for k,v in row.items() if k not in known})
    return dict(id=row.get('id',row.get('name')),status=row.get('status','passed' if row.get('ok') else 'failed'),duration_ms=row.get('duration_ms',int(round(row.get('elapsed',0)*1000))),extensions=extensions)
''',
'reports/canonical.py':'''import json
def dump_bytes(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
''',
'reports/serializer.py':'''import copy
from reports.upgrade import upgrade_record
from reports.canonical import dump_bytes
def serialize_report(rows,metadata):return dump_bytes(dict(version=2,extensions=copy.deepcopy(metadata),records=sorted([upgrade_record(x) for x in rows],key=lambda x:x['id'])))
'''}
def install(benchmark,row,w):
    if (w/'materialize.py').is_file():subprocess.run([sys.executable,str(w/'materialize.py')],cwd=w,check=True,capture_output=True)
    if row['adapter']=='original':
        assert row['task_name']=='sdk_compatibility_upgrade'
        for rel,text in SDK.items():write(w/rel,text)
        return
    dataset=benchmark/row['dataset_path'];reference=w/'_reference';reference.mkdir()
    for p in (dataset/'_authoring').iterdir():
        if p.is_file() and p.suffix in ('.py','.json'):shutil.copy2(p,reference/p.name)
    medium=benchmark/'medium26-extension-v1';templates=load(medium/'_authoring/templates.py','medium_templates_only')
    for cp in w.rglob('contract.json'):
        folder=cp.parent;depth=len(folder.relative_to(w).parts);write(folder/'model.py',templates.MODEL);write(folder/'render.py',templates.RENDER.replace('DEPTH',str(depth)))
        write(folder/'transform.py',f'import sys\nfrom pathlib import Path\nROOT=Path(__file__).resolve().parents[{depth}]\nsys.path.insert(0,str(ROOT/"_reference"))\nfrom reference import evaluate\ndef transform(payloads,contract):return evaluate(payloads,contract)\n')
    if row['adapter']=='medium':write(w/'run_all.py',templates.RUN_ALL);write(w/'final_report.py',templates.FINAL.replace('TITLE_LITERAL',repr(row['title'])))
    else:
        spec=json.loads((dataset/'_authoring/task_specs.json').read_text(encoding='utf-8'))[row['entry_id']];write(w/'run_all.py',HARD_RUN)
        write(w/'final_report.py',f'import sys,json\nfrom pathlib import Path\nROOT=Path(__file__).resolve().parent\nsys.path.insert(0,str(ROOT/"_reference"))\nfrom reference import final_report\ncore=json.loads((ROOT/"outputs/core_manifest.json").read_text(encoding="utf-8"))\n(ROOT/"outputs/final_report.json").write_text(json.dumps(final_report(core,{spec["title"]!r}),ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\\n",encoding="utf-8")\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--benchmark-root',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();benchmark=a.benchmark_root.resolve();work=a.work.resolve()
    if work.exists():raise ValueError('refusing existing QA work directory')
    work.mkdir(parents=True);catalog=json.loads((HERE/'catalog.json').read_text(encoding='utf-8'));policy=json.loads((HERE/'policy.json').read_text(encoding='utf-8'));tests=[]
    for difficulty,maximum in [('E',1),('M',2),('H',3)]:
        assert reward(10,10,difficulty,policy)['reward']==maximum;assert reward(5,10,difficulty,policy)['reward']==maximum/2;assert reward(10,10,difficulty,policy,False)['reward']==0
    assert reward(1,3,'E',policy)['reward']==.333333;assert reward(2,3,'M',policy)['reward']==1.333333
    for invalid in [(0,0),(-1,3),(4,3),(True,3)]:
        try:reward(*invalid,'M',policy)
        except ValueError:pass
        else:raise AssertionError('bad counts accepted')
    def score(key,w,label):
        out=work/(key.replace('/','_')+'_'+label+'.json');p=subprocess.run([sys.executable,str(HERE/'score.py'),'--benchmark-root',str(benchmark),'--task',key,'--workspace',str(w),'--json-output',str(out)],capture_output=True,text=True,timeout=600)
        if p.returncode:raise RuntimeError(key+' '+label+' '+p.stdout[-1000:]+' '+p.stderr[-1000:])
        return json.loads(out.read_text(encoding='utf-8'))
    def one(item):
        key,row=item;w=work/key.replace('/','_');shutil.copytree(benchmark/row['source_task']/'workspace',w);empty=score(key,w,'empty');assert empty['reward']==0,(key,empty['reward']);record=dict(task=key,empty_reward=0)
        if row['adapter']!='original' or row['task_name']=='sdk_compatibility_upgrade':
            install(benchmark,row,w);full=score(key,w,'reference');assert full['all_checks_passed'] and full['reward']==policy['difficulty_max_reward'][row['difficulty']],(key,full['reward'],[x for x in full['checks'] if not x['passed']]);record.update(reference_reward=full['reward'],verifier_count=full['total_verifiers'])
            if key in ('medium/MP01','hard/identity_federation_transition_spec_v4','original/sdk_compatibility_upgrade'):
                check=w/'check.py';before=check.read_bytes();check.write_bytes(before+b'\n# tampered\n');bad=score(key,w,'tampered');assert bad['reward']==0 and not bad['integrity_ok'];check.write_bytes(before);record['tamper_reward']=0
            if key=='medium/MP01':
                launcher=w/'run_all.py';before=launcher.read_bytes();launcher.write_bytes(before+b'\n(ROOT/"README.md").write_text("changed during execution",encoding="utf-8")\n');bad=score(key,w,'post_tampered');assert bad['reward']==0 and not bad['integrity_ok'];launcher.write_bytes(before);record['post_tamper_reward']=0
        print(json.dumps(record),flush=True);return record
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(one,catalog['tasks'].items()))
    freeze=json.loads((HERE/'task-content-freeze.json').read_text(encoding='utf-8'))
    for rel,digest in freeze['files'].items():assert hashlib.sha256((benchmark/rel).read_bytes()).hexdigest()==digest
    report=dict(status='passed',arithmetic_boundary_cases=15,empty_submissions_zero=len(results),full_reference_submissions=sum('reference_reward' in r for r in results),reference_by_difficulty={d:sum('reference_reward' in r and catalog['tasks'][r['task']]['difficulty']==d for r in results) for d in ['E','M','H']},tamper_submissions_zero=sum('tamper_reward' in r for r in results)+sum('post_tamper_reward' in r for r in results),unchanged_task_files=freeze['file_count'],model_requests=0,results=results)
    (work/'validation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
