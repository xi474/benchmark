"""Reproducible author QA; temporary solutions never enter delivered workspaces."""
from __future__ import annotations
import argparse
import concurrent.futures
import copy
import hashlib
import itertools
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

def reference_audit():
    from reference import weighted,checkpoint,assignment,dag,trace,logparse,windows,policy,compatibility,graphimpact
    from specification import fixture
    # Brute force independently confirms both scheduling objective and its tricky zero-value tie.
    for seed in range(20):
        p=fixture('weighted_intervals',seed); p['windows']=p['windows'][:8]; cooldown=seed%3
        candidates=[]
        for bits in itertools.product((False,True),repeat=len(p['windows'])):
            chosen=[r for r,b in zip(p['windows'],bits) if b]
            ordered=sorted(chosen,key=lambda r:(r['start'],r['end']))
            if any(a['end']+cooldown>b['start'] for a,b in zip(ordered,ordered[1:])): continue
            candidates.append((sum(r['value'] for r in chosen),sorted(r['id'] for r in chosen)))
        best=min(candidates,key=lambda r:(-r[0],r[1]))
        assert weighted(p,dict(cooldown=cooldown))==dict(value=best[0],selected=best[1])
    assert weighted({'windows':[dict(id='a',start=0,end=1,value=0),dict(id='b',start=5,end=6,value=2)]},dict(cooldown=0))==dict(selected=['a','b'],value=2)
    assert checkpoint(dict(checkpoints=[],events=[dict(partition='p',offset=0,epoch=1,committed=True),dict(partition='p',offset=2,epoch=1,committed=True)]))==dict(next_offsets={'p':1},applied=['p:0'],pending={'p':[2]})
    ap=dict(jobs=[dict(id='a',skill='x',duration=1),dict(id='b',skill='x',duration=1)],workers=[dict(id=w,skills=['x'],capacity=1,cost=1,affinity={}) for w in ['z','y']])
    assert assignment(ap,[])==dict(feasible=True,score=0,cost=2,assignments=[dict(job='a',worker='y'),dict(job='b',worker='z')])
    assert dag({'nodes':[dict(id='a',duration=2,deps=[]),dict(id='b',duration=2,deps=[]),dict(id='c',duration=3,deps=['b','a'])]})['critical_path']==['a','c']
    assert trace({'spans':[dict(id='a',service='API',duration=2,error=False,children=[dict(id='b',service='DB',duration=3,error=True)])]})==dict(error_services=['db'],critical_path=['a','b'],duration=5,span_count=2)
    assert logparse({'lines':['ERROR token="a b" password=x; secret = y']})['lines']==['ERROR token=[REDACTED] password=[REDACTED]; secret=[REDACTED]']
    assert windows({'events':[dict(id=str(i),revision=0,ts=0,key='k',value=i) for i in range(1,21)]},{'window_size':10})['windows'][0]['p95']==19
    assert compatibility({'old':[dict(name='x',type='int',required=False)],'new':[dict(name='x',type='float',required=False)]})['compatible']
    assert policy({'rules':[],'requests':[dict(resource='x',action='read')]})['decisions'][0]['effect']=='deny'
    assert graphimpact({'edges':[['a','b'],['b','a'],['b','c']],'seeds':['a']})==dict(distances={'a':0,'b':1,'c':2},components=[['a','b'],['c']])
    from strengthening import independent_audit
    return 30+independent_audit()

def install_reference(w,spec,author):
    import build
    if (w/'materialize.py').exists():
        subprocess.run([sys.executable,str(w/'materialize.py')],cwd=w,check=True,capture_output=True)
    for s in spec['specs']:
        p=w/s['folder']; depth=len(Path(s['folder']).parts)
        build.write(p/'model.py',build.MODEL)
        build.write(p/'transform.py',f'''import sys
from pathlib import Path
sys.path.insert(0,{str(author)!r})
from reference import evaluate
def transform(payloads,contract):
    return evaluate(payloads,contract)
''')
        build.write(p/'render.py',build.RENDER.replace('ROOT_DEPTH',str(depth)))
    build.write(w/'final_report.py',f'''import sys,json
from pathlib import Path
sys.path.insert(0,{str(author)!r})
from reference import final_report
ROOT=Path(__file__).resolve().parent
core=json.loads((ROOT/'outputs/core_manifest.json').read_text(encoding='utf-8'))
report=final_report(core,{spec['title']!r})
(ROOT/'outputs/final_report.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\\n',encoding='utf-8')
''')
    build.write(w/'run_all.py','''import json,sys,subprocess,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
out=ROOT/'outputs'
if out.is_symlink(): raise ValueError('outputs symlink')
if out.exists(): shutil.rmtree(out)
def run(*args): subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,check=True)
if (ROOT/'materialize.py').exists(): run(ROOT/'materialize.py')
pending=[(p,json.loads(p.read_text(encoding='utf-8'))) for p in sorted(ROOT.rglob('contract.json'))]
while pending:
    progress=False
    for p,c in list(pending):
        if not all((ROOT/rel).exists() for rel in c['inputs']): continue
        run(p.with_name('render.py')); pending.remove((p,c)); progress=True
    needs_core=any('outputs/domain_core.json' in c['inputs'] for p,c in pending)
    domains=[json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'domains').glob('*/contract.json')]
    if needs_core and domains and all((ROOT/c['output']).exists() for c in domains) and not (ROOT/'outputs/domain_core.json').exists():
        run(ROOT/'integrate.py','domains'); progress=True
    if not progress: raise ValueError('unresolved input dependencies')
run(ROOT/'integrate.py'); run(ROOT/'final_report.py')
''')

def reject(action,label):
    try: action()
    except (AssertionError,ValueError,subprocess.SubprocessError,KeyError): return label
    raise AssertionError('mutation escaped: '+label)

def check_entry(root,key,spec):
    import verify
    with tempfile.TemporaryDirectory(prefix='mixed16-v2-qa-',dir=root.parent) as tmp:
        w=Path(tmp)/'workspace'; shutil.copytree(root/'tasks'/key/'workspace',w)
        initial=subprocess.run([sys.executable,str(w/'check.py')],cwd=w,capture_output=True,timeout=30)
        assert initial.returncode!=0,'initial workspace passed'
        install_reference(w,spec,root/'_authoring')
        result=verify.verify(key,w)
        negatives=[]
        check=w/'check.py'; original=check.read_bytes()
        try:
            check.write_text("print('PASS')\n",encoding='utf-8')
            negatives.append(reject(lambda:verify.verify(key,w),'checker_tampering'))
        finally: check.write_bytes(original)
        contract=w/spec['specs'][0]['folder']/'contract.json'; original=contract.read_bytes()
        try:
            contract.write_text('{}\n',encoding='utf-8')
            negatives.append(reject(lambda:verify.verify(key,w),'contract_tampering'))
        finally: contract.write_bytes(original)
        report=w/'final_report.py'; original=report.read_bytes()
        try:
            report.write_bytes(original+b"\np=ROOT/'outputs/final_report.json'\nr=json.loads(p.read_text(encoding='utf-8')); r['sha256']='0'*64\np.write_text(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+'\\n',encoding='utf-8')\n")
            negatives.append(reject(lambda:verify.verify(key,w),'incorrect_final_output'))
        finally: report.write_bytes(original)
        available,expected=verify.expected_outputs(spec)
        first=spec['specs'][0]; transform=w/first['folder']/'transform.py'; original=transform.read_bytes()
        try:
            baseline=expected[first['contract']['output']]
            transform.write_text(f'def transform(payloads,contract):\n    return {baseline!r}\n',encoding='utf-8')
            negatives.append(reject(lambda:verify.probes(w,spec,available,only=first['folder']),'public_fixture_hardcoding'))
        finally: transform.write_bytes(original)
        from strengthening import TARGETS
        if key.split('/')[-1] in TARGETS:
            consumer=spec['specs'][-1]; transform=w/consumer['folder']/'transform.py'; original=transform.read_bytes()
            frozen=[available[p] for p in consumer['contract']['inputs'][1:]]
            try:
                transform.write_text(f'import sys\nsys.path.insert(0,{str(root / "_authoring")!r})\nfrom reference import evaluate\ndef transform(payloads,contract):\n    return evaluate([payloads[0]]+{frozen!r},contract)\n',encoding='utf-8')
                negatives.append(reject(lambda:verify.probes(w,spec,available,only=consumer['folder']),'upstream_result_ignored'))
            finally: transform.write_bytes(original)
            names={'api_deprecation_campaign':'notice_coverage','identity_federation_transition':'session_replay','search_index_rebuild':'schema_migration','certificate_rotation_readiness':'trust_paths','backup_restore_certification':'transaction_replay','observability_retention_upgrade':'retention_optimizer','network_policy_convergence':'ecmp_routes'}
            faulty=next(s for s in spec['specs'] if s['contract']['operation']==names[key.split('/')[-1]])
            transform=w/faulty['folder']/'transform.py'; original=transform.read_bytes()
            try:
                transform.write_text(f'import sys\nsys.path.insert(0,{str(root / "_authoring")!r})\nfrom strengthening import algorithm_mutant\ndef transform(payloads,contract):\n    return algorithm_mutant(payloads,contract)\n',encoding='utf-8')
                negatives.append(reject(lambda:verify.probes(w,spec,available,only=faulty['folder']),'incorrect_algorithm_shortcut'))
            finally: transform.write_bytes(original)
        if spec['suite']=='multistage4':
            domains=[s for s in spec['specs'] if s['folder'].startswith('domains/')]
            a,b=[w/s['contract']['output'] for s in domains[:2]]
            original=b.read_bytes()
            try:
                ra=json.loads(a.read_text(encoding='utf-8')); rb=json.loads(b.read_text(encoding='utf-8'))
                conflict=copy.deepcopy(ra['result']['records'][0]); conflict['score']=(conflict['score']+1)%21
                rb['result']['records'].append(conflict); b.write_text(json.dumps(rb),encoding='utf-8')
                run=subprocess.run([sys.executable,str(w/'integrate.py'),'domains'],cwd=w,capture_output=True,timeout=20)
                assert run.returncode!=0,'integration conflict accepted'
                negatives.append('integration_conflict')
            finally: b.write_bytes(original)
        result.update(initial_workspace_failed=True,reference_passed=True,rejected_mutations=negatives)
        return result

def checksums(root):
    lines=[]
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.name!='SHA256SUMS' and '__pycache__' not in p.parts:
            lines.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(root).as_posix())
    (root/'SHA256SUMS').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')

def structure_audit(spec):
    nodes={s['contract']['name']:set() for s in spec['specs']}
    owners={s['contract']['output']:s['contract']['name'] for s in spec['specs']}
    domains={s['contract']['name'] for s in spec['specs'] if s['folder'].startswith('domains/')}
    if any('outputs/domain_core.json' in s['contract']['inputs'] for s in spec['specs']):
        nodes['<domain integration>']=domains
        owners['outputs/domain_core.json']='<domain integration>'
    for s in spec['specs']:
        nodes[s['contract']['name']]={owners[p] for p in s['contract']['inputs'] if p in owners}
    if spec['suite']=='linux2':
        for deps in nodes.values(): deps.add('<materialization>')
        nodes['<materialization>']=set()
    nodes['<core integration>']={s['contract']['name'] for s in spec['specs']}
    nodes['<final report>']={'<core integration>'}
    done=set(); waves=[]
    while len(done)<len(nodes):
        ready={n for n,deps in nodes.items() if n not in done and deps<=done}
        assert ready,'dependency cycle'
        waves.append(len(ready)); done.update(ready)
    ancestors={n:set(deps) for n,deps in nodes.items()}
    for _ in nodes:
        for n in nodes: ancestors[n].update(set().union(*(ancestors[d] for d in list(ancestors[n]))) if ancestors[n] else set())
    width=0; keys=sorted(nodes)
    for mask in range(1<<len(keys)):
        members=[n for i,n in enumerate(keys) if mask&(1<<i)]
        if len(members)<=width: continue
        if all(a not in ancestors[b] and b not in ancestors[a] for a,b in itertools.combinations(members,2)): width=len(members)
    return dict(maximum_independent_frontier=width,earliest_layer_sizes=waves,layer_count=len(waves),component_count=len(spec['specs']))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,required=True); args=p.parse_args(); root=args.root.resolve()
    sys.path.insert(0,str(root/'verifier')); sys.path.insert(0,str(root/'_authoring'))
    import verify
    specs=json.loads((root/'_authoring/task_specs.json').read_text(encoding='utf-8'))
    audits=reference_audit(); results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(check_entry,root,key,spec):key for key,spec in specs.items()}
        for future in concurrent.futures.as_completed(futures):
            result=future.result(); results.append(result)
            print('VALIDATED',result['entry'],'api_cases='+str(result['api_cases']),'rejected='+str(len(result['rejected_mutations'])),flush=True)
    structures={key:structure_audit(spec) for key,spec in specs.items()}
    assert {2,3,4}<=set(v['maximum_independent_frontier'] for v in structures.values()),'insufficient frontier diversity'
    (root/'_authoring/structure_audit.json').write_text(json.dumps(structures,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    from strengthening import duplicate_audit
    uniqueness=duplicate_audit(root,specs)
    (root/'_authoring/duplicate_audit.json').write_text(json.dumps(uniqueness,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    report=dict(version='3.0.0',entry_count=len(results),all_passed=all(r['reference_passed'] and r['initial_workspace_failed'] for r in results),reference_independent_audits=audits,
        api_case_count=sum(r['api_cases'] for r in results),rejected_mutation_count=sum(len(r['rejected_mutations']) for r in results),task_level_duplicates=uniqueness['task_level_duplicates'],shared_component_fixture_groups=len(uniqueness['duplicate_groups']['component_input']),entries=sorted(results,key=lambda r:r['entry']),
        note='Correctness and regression validation only; no measured agent speedup or scheduling-classification results.')
    (root/'_authoring/validation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    checksums(root); print('ALL_16_VALIDATED',flush=True)

if __name__=='__main__': main()
