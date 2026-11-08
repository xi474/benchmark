"""Run optional robustness independently; no core reward or difficulty gate."""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'partial_reward'))
import score
import adapters

def main():
    p=argparse.ArgumentParser();p.add_argument('--benchmark-root',type=Path,required=True);p.add_argument('--task',required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--json-output',type=Path);a=p.parse_args()
    root=a.benchmark_root.resolve();source=a.workspace.resolve()
    catalog=json.loads((HERE/'partial_reward/catalog.json').read_text(encoding='utf-8'));row=catalog['tasks'][a.task]
    checks=adapters.robustness_checks(root,row)
    assert len(checks)==row['robustness_verifier_count'] and score.check_digest(checks)==row['robustness_checks_sha256']
    violations=score.protected(source,row);results=[]
    if not violations:
        with tempfile.TemporaryDirectory(prefix='core6-robustness-') as td:
            w=Path(td)/'workspace';shutil.copytree(source,w,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            if (w/'materialize.py').is_file():score.command([sys.executable,str(w/'materialize.py')],w)
            for c in checks:
                passed,detail=score.evaluate(c,w,{})
                results.append(dict(id=c['id'],category=c['category'],passed=passed,detail=detail))
            violations=score.protected(w,row,post=True)
    if not results:results=[dict(id=c['id'],category=c['category'],passed=False,detail='blocked by integrity') for c in checks]
    passed=sum(c['passed'] for c in results)
    result=dict(schema='adapted6.optional-robustness.v3',task=a.task,scope='optional_robustness_only',
                affects_core_reward=False,affects_difficulty=False,integrity_ok=not violations,
                passed_verifiers=passed,total_verifiers=len(checks),pass_ratio=passed/len(checks) if not violations else 0,
                all_checks_passed=not violations and passed==len(checks),checks=results,integrity_violations=violations)
    if a.json_output:a.json_output.parent.mkdir(parents=True,exist_ok=True);a.json_output.write_text(score.dump(result),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False))
    return 0

if __name__=='__main__':sys.exit(main())
