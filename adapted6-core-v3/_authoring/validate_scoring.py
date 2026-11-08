"""Control positive, incomplete, core-only, wrong-business and tampered submissions."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();work=a.work.resolve();profiles=work/'scoring-profiles';assert not profiles.exists();profiles.mkdir()
    sys.path.insert(0,str(root/'_authoring'))
    from reference import TASKS
    from mutations import TARGETS
    rows=[]
    for t in TASKS:
        key='core6/'+t['id'];entry=t['style']+'/'+t['slug'];reference=work/t['id']
        for profile in ['initial','reference','core_only','wrong_business','tampered']:
            if profile=='initial':w=root/'tasks'/entry/'workspace'
            elif profile=='reference':w=reference
            else:
                w=profiles/(t['id']+'-'+profile);shutil.copytree(reference,w,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
                if profile=='core_only':
                    cp=w/'_solution/common.py';s=cp.read_text(encoding='utf-8')
                    helper='''def _without_optional_metadata(v):
    if type(v) is dict:return {k:_without_optional_metadata(x) for k,x in v.items() if not k.startswith('_')}
    if type(v) is list:return [_without_optional_metadata(x) for x in v]
    return v

'''
                    s=s.replace('def evaluate(payloads,contract):',helper+'def evaluate(payloads,contract):\n    payloads=_without_optional_metadata(payloads)')
                    cp.write_text(s,encoding='utf-8')
                elif profile=='wrong_business':
                    folder,c=next((f,c) for f,c in t['components'] if c['operation']==TARGETS[t['id']]);cp=w/folder/'transform.py'
                    prefix=cp.read_text(encoding='utf-8').split('\ndef transform',1)[0]
                    cp.write_text(prefix+'\nfrom mutations import mutate\ndef transform(payloads,contract):\n    return mutate('+repr(t['id'])+',evaluate(payloads,contract))\n',encoding='utf-8')
                else:(w/'check.py').write_bytes((w/'check.py').read_bytes()+b'\n# changed\n')
            out=profiles/(t['id']+'-'+profile+'.json')
            proc=subprocess.run([sys.executable,str(root/'verifier/partial_reward/score.py'),'--benchmark-root',str(root),'--task',key,'--workspace',str(w),'--json-output',str(out)],capture_output=True,text=True,timeout=180)
            assert proc.returncode==0,(key,profile,proc.stdout[-1000:],proc.stderr[-1000:])
            s=json.loads(out.read_text(encoding='utf-8'));assert s['robustness_affects_core_reward'] is False
            assert s['core_reward']==s['reward'] and s['all_checks_passed']==s['core_all_checks_passed']
            if profile=='initial':assert s['passed_verifiers']==0 and s['reward']==0
            elif profile=='reference':assert s['core_all_checks_passed'] and s['robustness_all_checks_passed'] and s['strict_all_checks_passed'] and s['reward']==2
            elif profile=='core_only':
                assert s['core_all_checks_passed'] and s['reward']==2 and not s['robustness_all_checks_passed'] and not s['strict_all_checks_passed']
                assert s['robustness_pass_ratio']==.25,(key,s['robustness_pass_ratio'])
                # Independent optional-only entry must report the same diagnostics.
                r=subprocess.run([sys.executable,str(root/'verifier/robustness.py'),'--benchmark-root',str(root),'--task',key,'--workspace',str(w)],capture_output=True,text=True,timeout=120)
                assert r.returncode==0,(key,r.stdout,r.stderr)
                rr=json.loads(r.stdout);assert rr['pass_ratio']==.25 and rr['affects_core_reward'] is False and 'reward' not in rr
            elif profile=='wrong_business':assert not s['core_all_checks_passed'] and s['reward']<2
            else:assert not s['integrity_ok'] and s['reward']==0 and not s['core_all_checks_passed']
            rows.append(dict(task=key,profile=profile,core_passed=s['passed_verifiers'],core_total=s['total_verifiers'],core_reward=s['reward'],core_full=s['core_all_checks_passed'],robustness_ratio=s['robustness_pass_ratio'],strict_full=s['strict_all_checks_passed'],integrity_ok=s['integrity_ok']))
        print('SCORER_QA',key,'all five profiles passed',flush=True)
    report=dict(status='passed',tasks=6,profiles=5,submissions=30,reference_core_and_robustness_full=6,initial_core_zero=6,
                core_only_full_reward_with_optional_failures=6,wrong_business_rejected=6,tampering_core_zero=6,
                independent_robustness_entry_checked=6,model_calls=0,rows=rows)
    (root/'review/scoring_v3_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
