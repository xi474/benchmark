"""Author-only exported-DAG smoke check; not an agent trajectory or speed benchmark."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def rows(p):
    return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--package',type=Path,required=True)
    p.add_argument('--export',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sys.path.insert(0,str(a.package/'verifier'))
    from score import compare, protected, pointer
    graphs={r['task_id']:r for r in rows(a.export/'graphs.jsonl')}
    states={(r['task_id'],tuple(r['completed_component_ids'])):r for r in rows(a.export/'ready_states.jsonl')}
    catalog=read(a.package/'verifier/catalog.json')['tasks']
    reports=[]
    with tempfile.TemporaryDirectory(prefix='medium30-parallel-smoke-') as tmp:
        for ident,row in catalog.items():
            work=Path(tmp)/ident
            shutil.copytree(a.package/row['entry']/'workspace',work)
            for src in (a.package/'_authoring/authoring').glob('references*.py'):
                shutil.copyfile(src,work/src.name)
            workflow=read(work/'workflow.json')
            components={ident+'::'+c['name']:c for c in workflow['components']}
            for c in components.values():
                (work/c['folder']/'engine.py').write_text('from runtime import build,read\nfrom references import solve\ndef transform(payload,contract):return solve(contract["op"],payload,contract)\ndef load_payload(path):return read(path)\ndef build_component(root,contract):return build(root,contract,transform)\n',encoding='utf-8')
            graph=graphs[ident]
            assert set(graph['nodes'])==set(components)
            dependencies={n:{u for u,v in graph['edges'] if v==n} for n in components}
            case=read(a.package/row['vectors'])['integration'][0]
            # This is the published initial input, not a newly generated fixture.
            assert read(work/'inputs/request.json')==case['input']
            done=set();batches=[]
            def execute(node):
                start=time.monotonic()
                folder=components[node]['folder']
                code='import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from runtime import module,read;r=Path(sys.argv[1]);f=sys.argv[2];api=module(r,f+"/engine.py");api.build_component(r,read(r/f/"contract.json"))'
                proc=subprocess.run([sys.executable,'-c',code,str(work),folder],cwd=work,capture_output=True,text=True,timeout=180)
                assert proc.returncode==0,(ident,node,proc.stderr[-2000:])
                return dict(node=node,start_seconds=start,end_seconds=time.monotonic())
            while True:
                ready=sorted(n for n in components if n not in done and dependencies[n]<=done)
                exported=states[(ident,tuple(sorted(done)))]
                assert ready==exported['ready_component_ids']
                if len(done)==len(components):
                    assert exported['is_terminal']
                    break
                assert ready,(ident,'cycle')
                with ThreadPoolExecutor(max_workers=2) as pool:
                    spans=list(pool.map(execute,ready))
                batches.append(dict(completed_before=sorted(done),ready=ready,process_intervals=spans))
                done.update(ready)
            artifacts=0
            for node,c in components.items():
                name=c['name'];contract=read(work/c['folder']/'contract.json')
                actual=read(work/contract['output']);wanted=case['results'][name]
                assert compare(ident,name,actual,wanted,case['input']),(ident,name,'canonical')
                for path,item in contract.get('emit',{}).items():
                    dest=work/path;fmt=item['format']
                    if fmt=='text':value=dest.read_text(encoding='utf-8')
                    elif fmt=='json':value=read(dest)
                    elif fmt=='ics':
                        from semantic import ics_record
                        value=ics_record(dest.read_text(encoding='utf-8'))
                    elif fmt=='base64':value=base64.b64encode(dest.read_bytes()).decode()
                    else:
                        import numpy as np
                        value=np.load(dest,allow_pickle=False).tolist()
                    ok=value==pointer(wanted,item['pointer'])
                    if ident=='N26':ok=compare(ident,'distribution',value,{},case['input'])
                    elif ident=='N21':ok=compare(ident,'optimized_query',value,None,case['input'])
                    elif ident=='N25':ok=compare(ident,'deployment_hook',value,None,case['input'])
                    elif ident=='N15':
                        from semantic import archive_ok
                        ok=archive_ok({'tar':value,'rejected':wanted['rejected']},wanted)
                    elif ident=='N22' and name=='cleaned_repo':
                        from semantic import git_clean_ok
                        ok=git_clean_ok({**wanted,'bundle':value},wanted)
                    assert ok,(ident,path,'extra artifact')
                    artifacts+=1
            assert not protected(work,row['protected']),(ident,'protected')
            reports.append(dict(task_id=ident,status='passed',components=len(components),extra_artifacts=artifacts,ready_states_checked=len(batches)+1,batches=batches))
            print('PARALLEL_PIPELINE',ident,'PASS',flush=True)
    report=dict(status='passed',task_count=len(reports),workers=2,scope='author_reference_component_execution_not_agent_actions_or_speedup',graphs_sha256=hashlib.sha256((a.export/'graphs.jsonl').read_bytes()).hexdigest(),ready_states_sha256=hashlib.sha256((a.export/'ready_states.jsonl').read_bytes()).hexdigest(),results=reports)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
