"""Freeze verifier IDs/counts and integrity from existing, unchanged task packs."""
import argparse,hashlib,json,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def accepted(p):
    data=p.read_bytes();return sorted({hashlib.sha256(data).hexdigest(),hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()})
def files(root):return sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
def protected_name(rel):
    p=Path(rel)
    return p.suffix in ('.md','.json') or p.name in ('check.py','check_module.py','materialize.py','integrate.py')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--benchmark-root',required=True,type=Path);args=parser.parse_args();benchmark=args.benchmark_root.resolve();catalog=dict(schema='benchmark.verifier-catalog.v2',tasks={});fingerprints={};temp_parent=HERE/'_build_temp';temp_parent.mkdir(exist_ok=True)
    groups=[('original','E',benchmark/'manifest.json',''),('medium','M',benchmark/'medium26-extension-v1/manifest.json','medium26-extension-v1'),('hard','H',benchmark/'mixed16-precise-spec-v4/manifest.json','mixed16-precise-spec-v4/trusted_validation')]
    for kind,difficulty,manifest_path,dataset_path in groups:
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'));seen=set()
        for entry in manifest['entries']:
            if entry['task_name'] in seen:continue
            seen.add(entry['task_name']);entry_id=entry['entry_id'];key=kind+'/'+(entry['task_id'] if kind=='medium' else entry['task_name'])
            source_task=benchmark/('tasks/'+entry_id if kind=='original' else 'medium26-extension-v1/tasks/'+entry_id if kind=='medium' else 'mixed16-precise-spec-v4/tasks/'+entry_id);source=source_task/'workspace'
            for p in files(source_task):fingerprints[p.relative_to(benchmark).as_posix()]=sha(p)
            row=dict(adapter=kind if kind!='original' else 'original',difficulty=difficulty,entry_id=entry_id,dataset_path=dataset_path,source_task=source_task.relative_to(benchmark).as_posix(),task_name=entry['task_name'],title=entry.get('title',entry['task_name']),protected_initial={},protected_generated={},focused_folders=[])
            if kind in ('medium','hard'):
                dataset=benchmark/dataset_path;seal=json.loads((dataset/'verifier/protected_hashes.json').read_text(encoding='utf-8'))[entry_id]
                row['protected_initial']={rel:accepted(source/rel) for rel in seal['initial']}
                row['protected_generated']={rel:[digest] for rel,digest in seal['generated'].items()}
            else:
                row['protected_initial']={p.relative_to(source).as_posix():accepted(p) for p in files(source) if 'outputs' not in p.relative_to(source).parts and protected_name(p.relative_to(source).as_posix())}
                with tempfile.TemporaryDirectory(prefix='source-',dir=temp_parent) as temp:
                    work=Path(temp)/'workspace';shutil.copytree(source,work,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
                    if (work/'materialize.py').is_file():
                        proc=subprocess.run([sys.executable,str(work/'materialize.py')],cwd=work,capture_output=True,text=True,timeout=30)
                        if proc.returncode:raise RuntimeError('trusted original materializer failed '+key+' '+proc.stderr[-500:])
                    row['focused_folders']=sorted(p.parent.relative_to(work).as_posix() for p in files(work) if p.name=='check_module.py' and 'outputs' not in p.relative_to(work).parts)
                    for p in files(work):
                        rel=p.relative_to(work).as_posix()
                        if rel not in row['protected_initial'] and 'outputs' not in Path(rel).parts and protected_name(rel):row['protected_generated'][rel]=accepted(p)
            proc=subprocess.run([sys.executable,str(HERE/'score.py'),'--benchmark-root',str(benchmark),'--task',key,'--describe'],input=json.dumps(row),capture_output=True,text=True,encoding='utf-8',timeout=60)
            if proc.returncode:raise RuntimeError('describe failed '+key+' '+proc.stdout[-1000:]+' '+proc.stderr[-1000:])
            described=json.loads(proc.stdout);row.update(verifier_count=len(described['verifiers']),verifiers=described['verifiers'],checks_sha256=described['checks_sha256']);catalog['tasks'][key]=row
            print(key,row['verifier_count'],flush=True)
    assert len(catalog['tasks'])==56
    for p,digest in fingerprints.items():assert sha(benchmark/p)==digest,'source content changed '+p
    (HERE/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    (HERE/'task-content-freeze.json').write_text(json.dumps(dict(schema='task-content-freeze.v1',file_count=len(fingerprints),files=fingerprints),ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(tasks=56,original=14,medium=26,hard=16,source_files_unchanged=len(fingerprints)),ensure_ascii=False))
if __name__=='__main__':main()
