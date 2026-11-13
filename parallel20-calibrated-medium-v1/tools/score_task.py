"""Dispatch to the task's original frozen scorer in a separate Python process."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task',required=True)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--json-output',type=Path)
    p.add_argument('--reward-output',type=Path)
    args=p.parse_args()
    tasks=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))['tasks']
    selected=[r for r in tasks if r['id']==args.task]
    if len(selected)!=1:p.error('Unknown task ID')
    package=(ROOT/selected[0]['package']).resolve()
    assert package.is_relative_to(ROOT) and (package/'verifier/score.py').is_file()
    command=[sys.executable,'-B',str(package/'verifier/score.py'),'--package',str(package),'--task',args.task,'--workspace',str(args.workspace.resolve())]
    if args.json_output:command+=['--json-output',str(args.json_output.resolve())]
    if args.reward_output:command+=['--reward-output',str(args.reward_output.resolve())]
    return subprocess.run(command).returncode

if __name__=='__main__':raise SystemExit(main())
