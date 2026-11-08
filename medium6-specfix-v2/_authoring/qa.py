"""Author validation; never supplies solved workspaces to evaluated agents."""
from __future__ import annotations
import argparse,ast,collections,copy,hashlib,importlib.util,json,os,platform,shutil,subprocess,sys,time
from pathlib import Path
from reference import TASKS,OPS,canonical
from templates import MODEL,RENDER,RUN_ALL,FINAL
from vectors import available,variants
from oracles import run as oracle_checks
from mutations import TARGETS

def write(path,text):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8',newline='\n')
def sha(v):return hashlib.sha256(v).hexdigest()
def install(root,w,t):
    if (w/'materialize.py').is_file():subprocess.run([sys.executable,str(w/'materialize.py')],cwd=w,check=True,capture_output=True)
    solution=w/'_solution';solution.mkdir(exist_ok=True)
    for name in ['common.py','reference.py','algorithms_a.py','algorithms_b.py','algorithms_c.py','algorithms_d.py','candidate_metadata.json','mutations.py']:shutil.copy2(root/'_authoring'/name,solution/name)
    prefix='import sys\nfrom pathlib import Path\nsys.dont_write_bytecode=True\nROOT=Path(__file__).resolve().parents[DEPTH]\nsys.path.insert(0,str(ROOT/"_solution"))\nfrom reference import evaluate\n'
    for folder,c in t['components']:
        depth=len(Path(folder).parts);base=w/folder;write(base/'model.py',MODEL);write(base/'render.py',RENDER.replace('DEPTH',str(depth)));write(base/'transform.py',prefix.replace('DEPTH',str(depth))+'\ndef transform(payloads,contract):\n    return evaluate(payloads,contract)\n')
    write(w/'run_all.py',RUN_ALL);write(w/'final_report.py',FINAL.replace('TITLE_LITERAL',repr(t['title'])))
def must_reject(action,label):
    try:action()
    except Exception as exc:return dict(check=label,rejected=True,reason=str(exc)[:700])
    raise AssertionError('incorrectly accepted: '+label)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--work',required=True);args=parser.parse_args();root=Path(args.root).resolve();work=Path(args.work).resolve()
    if root==work or root in work.parents:raise ValueError('QA workspace must be outside release package')
    if work.exists():raise ValueError('refusing existing QA directory')
    work.mkdir(parents=True);scratch=work/'temp';scratch.mkdir();os.environ['MEDIUM26_TMPDIR']=str(scratch);sys.path.insert(0,str(root/'verifier'));spec=importlib.util.spec_from_file_location('official_medium26_verifier',root/'verifier/verify.py');verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    started=time.monotonic();oracle_results=oracle_checks();reports=[];negatives=[];stage_count=0
    for t in TASKS:
        entry=t['style']+'/'+t['slug'];w=work/t['id'];shutil.copytree(root/'tasks'/entry/'workspace',w)
        negatives.append(must_reject(lambda:verifier.verify(entry,w,api=False),t['id']+':initial_incomplete'))
        install(root,w,t);result=verifier.verify(entry,w);reports.append(result);stage_count+=len(t['components']);print(json.dumps(dict(id=t['id'],reference='passed',api_cases=result['api_cases']),ensure_ascii=False),flush=True)
        saved={folder:(w/folder/'transform.py').read_text(encoding='utf-8') for folder,c in t['components']};a=available(t,t['fixture'](47))
        # Public-constant implementations are rejected by actual official API probes.
        for folder,c in t['components']:write(w/folder/'transform.py','def transform(payloads,contract):\n    return '+repr(a[c['output']])+'\n')
        negatives.append(must_reject(lambda:verifier.probe(w,t),t['id']+':hardcoded_public_API'))
        for folder,content in saved.items():write(w/folder/'transform.py',content)
        # Cache only upstream results while preserving changed raw local inputs.
        dependent=next(((folder,c) for folder,c in reversed(t['components']) if any(x.startswith('outputs/') for x in c['inputs'])),None)
        if dependent:
            folder,c=dependent;cached={i:a[path] for i,path in enumerate(c['inputs']) if path.startswith('outputs/')};prefix=saved[folder].split('\ndef transform',1)[0]
            text=prefix+'\nimport copy\nCACHED='+repr(cached)+'\ndef transform(payloads,contract):\n    actual=copy.deepcopy(payloads)\n    for i,value in CACHED.items():actual[i]=copy.deepcopy(value)\n    return evaluate(actual,contract)\n'
            write(w/folder/'transform.py',text);negatives.append(must_reject(lambda:verifier.probe(w,t,only=c['name']),t['id']+':cached_upstream_API'));write(w/folder/'transform.py',saved[folder])
        folder,c=next((folder,c) for folder,c in t['components'] if c['operation']==TARGETS[t['id']]);prefix=saved[folder].split('\ndef transform',1)[0]
        write(w/folder/'transform.py',prefix+'\nfrom mutations import mutate\ndef transform(payloads,contract):\n    return mutate('+repr(t['id'])+',evaluate(payloads,contract))\n')
        negatives.append(must_reject(lambda:verifier.probe(w,t,only=c['name']),t['id']+':semantic_mutation_API'));write(w/folder/'transform.py',saved[folder])
        protected=w/'check.py';before=protected.read_bytes();protected.write_bytes(before+b'\n# changed\n');seal=json.loads((root/'verifier/protected_hashes.json').read_text(encoding='utf-8'))[entry]
        negatives.append(must_reject(lambda:verifier.integrity(w,seal),t['id']+':protected_check_tamper'));protected.write_bytes(before)
    metadata=json.loads((root/'manifest.json').read_text(encoding='utf-8'));families=collections.defaultdict(list)
    for t in TASKS:families[t['source_metadata']['family']].append(t['id'])
    def duplicates(pairs):
        by=collections.defaultdict(list)
        for id_,fingerprint in pairs:by[fingerprint].append(id_)
        return [ids for ids in by.values() if len(ids)>1]
    dupe=dict(exact_task_prompt_duplicates=duplicates([(x['task_id'],x['task_prompt_sha256']) for x in metadata['entries']]),exact_initial_workspace_duplicates=duplicates([(x['task_id'],x['workspace_tree_sha256']) for x in metadata['entries']]),exact_public_input_duplicates=duplicates([(t['id'],sha(canonical(t['fixture'](47)).encode())) for t in TASKS]),related_task_families={k:v for k,v in families.items() if len(v)>1},family_count=len(families),scope='Exact prompt/workspace/input fingerprints plus manual semantic families; not a proof of full semantic independence.')
    assert not dupe['exact_task_prompt_duplicates'] and not dupe['exact_initial_workspace_duplicates'] and not dupe['exact_public_input_duplicates']
    report=dict(status='passed',task_count=len(TASKS),core_components=stage_count,reference_passed=len(reports),initial_incomplete_rejected=sum(x['check'].endswith(':initial_incomplete') for x in negatives),hardcoded_public_API_rejected=sum(x['check'].endswith(':hardcoded_public_API') for x in negatives),cached_upstream_API_rejected=sum(x['check'].endswith(':cached_upstream_API') for x in negatives),semantic_mutation_API_rejected=sum(x['check'].endswith(':semantic_mutation_API') for x in negatives),protected_tamper_rejected=sum(x['check'].endswith(':protected_check_tamper') for x in negatives),api_cases=sum(x['api_cases'] for x in reports),loader_render_cases=sum(x['loader_render_cases'] for x in reports),independent_oracle_groups=len(oracle_results),independent_oracles=oracle_results,python=sys.version,platform=platform.platform(),elapsed_seconds=round(time.monotonic()-started,2),model_runs=0,parallel_speedup_measured=False,source_benchmark_equivalence=False,entries=reports,negative_checks=negatives)
    review=root/'review';write(review/'validation_report.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n');write(review/'duplicate_audit.json',json.dumps(dupe,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['entries','negative_checks','independent_oracles']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
