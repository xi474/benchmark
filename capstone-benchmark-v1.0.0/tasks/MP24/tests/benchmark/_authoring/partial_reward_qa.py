import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--reference-work',type=Path,required=True);args=p.parse_args()
    root=args.root.resolve();refs=args.reference_work.resolve();manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'));results=[]
    with tempfile.TemporaryDirectory(prefix='medium26-v2-partial-') as td:
        temp=Path(td)
        for e in manifest['entries']:
            for arm in ['initial','reference']:
                w=root/'tasks'/e['entry_id']/'workspace' if arm=='initial' else refs/e['task_id']
                output=temp/f'{e["task_id"]}-{arm}.json'
                proc=subprocess.run([sys.executable,str(root/'verifier/partial_reward/score.py'),'--benchmark-root',str(root),'--task','core6/'+e['task_id'],'--workspace',str(w),'--scratch',str(temp),'--json-output',str(output)],capture_output=True,text=True,encoding='utf-8',timeout=120)
                assert proc.returncode==0,(e['task_id'],arm,proc.stdout[-1000:],proc.stderr[-1000:])
                s=json.loads(output.read_text(encoding='utf-8'));assert s['integrity_ok']
                assert s['passed_verifiers']==(0 if arm=='initial' else s['total_verifiers']),(e['task_id'],arm,s['passed_verifiers'],s['total_verifiers'])
                assert s['all_checks_passed']==(arm=='reference')
                results.append({'task_id':e['task_id'],'arm':arm,'passed_verifiers':s['passed_verifiers'],'total_verifiers':s['total_verifiers'],'reward':s['reward'],'max_reward':s['max_reward'],'checks_sha256':s['checks_sha256']})
            print(json.dumps({'task':e['task_id'],'initial':'0','reference':'full'},ensure_ascii=False),flush=True)
    result={'status':'passed','tasks':len(manifest['entries']),'initial_zero_reward':len(manifest['entries']),'reference_full_reward':len(manifest['entries']),'model_calls':0,'results':results}
    (root/'review/partial_reward_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False))


if __name__=='__main__':main()
