"""Export unchanged task inputs with an external fractional-reward test adapter."""
import argparse,hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8',newline='\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--benchmark-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--task',action='append');p.add_argument('--tier',choices=['original','medium','hard','all'],default='all');p.add_argument('--base-image',default='pilot10-common:20261031');a=p.parse_args();benchmark=a.benchmark_root.resolve();out=a.output.resolve()
    if out.exists():raise ValueError('refusing existing export directory')
    catalog=json.loads((HERE/'catalog.json').read_text(encoding='utf-8'));selected={k:r for k,r in catalog['tasks'].items() if (a.tier=='all' or r['adapter']==a.tier) and (not a.task or k in a.task)}
    if not selected or a.task and set(selected)!=set(a.task):raise ValueError('unknown/mismatched task selection')
    records=[]
    for key,row in selected.items():
        dest=out/('reward-v2-'+key.replace('/','-'));source=benchmark/row['source_task'];env=dest/'environment';tests=dest/'tests';env.mkdir(parents=True);tests.mkdir();shutil.copy2(source/'TASK.md',dest/'instruction.md');shutil.copytree(source/'workspace',env/'workspace',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for f in (source/'workspace').rglob('*'):
            if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc':assert sha(f)==sha(env/'workspace'/f.relative_to(source/'workspace'))
        assert sha(source/'TASK.md')==sha(dest/'instruction.md')
        shutil.copytree(HERE,tests/'evaluation-v2',ignore=shutil.ignore_patterns('__pycache__','*.pyc','_build_temp'))
        bench=tests/'benchmark';bench.mkdir()
        if row['adapter']!='original':
            dataset=benchmark/row['dataset_path'];target=bench/row['dataset_path'];target.mkdir(parents=True)
            for folder in ['_authoring','verifier']:shutil.copytree(dataset/folder,target/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc','dags'))
        write(env/'Dockerfile',f'FROM {a.base_image}\nWORKDIR /app\nCOPY workspace/ /app/\n')
        write(tests/'Dockerfile',f'FROM {a.base_image}\nWORKDIR /tests\nCOPY . /tests\n')
        write(tests/'test.sh',f'''#!/bin/bash
set -u
mkdir -p /logs/verifier
python3 /tests/evaluation-v2/score.py --benchmark-root /tests/benchmark --task {key} --workspace /app --json-output /logs/verifier/score-v2.json --reward-output /logs/verifier/reward.txt
exit "$?"
''')
        write(dest/'task.toml',f'''schema_version = "1.0"
version = "2.0.0"
artifacts = ["/app"]
[task]
name = "reward-v2/{key.replace('/','-')}"
version = "2.0.0"
description = "Existing task with count-based difficulty-weighted reward"
[metadata]
source_task = "{row['source_task']}"
evaluation_version = "reward-v2"
[verifier]
environment_mode = "separate"
timeout_sec = 1800.0
[agent]
timeout_sec = 3600.0
[environment]
cpus = 2
memory_mb = 4096
storage_mb = 10240
build_timeout_sec = 900.0
''')
        records.append(dict(task=key,directory=dest.name,difficulty=row['difficulty'],task_content_unchanged=True))
    write(out/'export-manifest.json',json.dumps(dict(evaluation_version='2.0.0',entries=records),ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(tasks=len(records),output=str(out),task_content_unchanged=True),ensure_ascii=False))
if __name__=='__main__':main()
