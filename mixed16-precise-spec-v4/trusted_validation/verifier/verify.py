"""Official verifier. Keep this directory and _authoring read-only and off agent mounts."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'_authoring'))
from reference import evaluate, records_from, final_report
from specification import fixture, empty, invalid

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def integrity(workspace,seal,post=False):
    for rel,expected in seal['initial'].items():
        path=workspace/rel
        assert path.is_file() and not path.is_symlink() and digest(path)==expected,'protected file changed: '+rel
    for rel,expected in seal['generated'].items():
        path=workspace/rel
        if post or path.exists():
            assert path.is_file() and not path.is_symlink() and digest(path)==expected,'generated protected file changed: '+rel

def expected_outputs(spec):
    available=copy.deepcopy(spec['inputs']); outputs={}; pending=list(spec['specs'])
    needs_core=any('outputs/domain_core.json' in s['contract']['inputs'] for s in pending)
    while pending:
        progress=False
        if needs_core and 'outputs/domain_core.json' not in available:
            domains=[s['contract']['output'] for s in spec['specs'] if s['folder'].startswith('domains/')]
            if all(p in available for p in domains):
                value={'name':'domain_core','result':{'records':records_from([available[p] for p in domains])}}
                available['outputs/domain_core.json']=outputs['outputs/domain_core.json']=value; progress=True
        for s in list(pending):
            c=s['contract']
            if not all(rel in available for rel in c['inputs']): continue
            value=evaluate([available[rel] for rel in c['inputs']],c)
            available[c['output']]=outputs[c['output']]=value
            pending.remove(s); progress=True
        assert progress,'invalid author dependency specification'
    core={'components':dict(sorted((s['contract']['name'],available[s['contract']['output']]['result']) for s in spec['specs']))}
    outputs['outputs/core_manifest.json']=core
    outputs['outputs/final_report.json']=final_report(core,spec['title'])
    return available,outputs

def vectors(spec,s,available):
    c=s['contract']; op=c['operation']; original=[copy.deepcopy(available[p]) for p in c['inputs']]
    from strengthening import NEW_RULES, new_vectors
    if op in NEW_RULES: return new_vectors(spec,s,original)
    cases=[dict(payloads=original,contract=copy.deepcopy(c))]
    if op in ('risk_ranking','review_balance','remediation_plan'):
        base=[]
        for j in range(13):
            base.append(dict(id=f'x{j}',source='heldout',owner=['ops','data'][j%2],category=['prepare','copy','verify'][j%3],tags=['blocking'] if j%2 else [],score=(j*7+spec['index'])%21))
        for rows in ([],base,list(reversed(base)),base+copy.deepcopy(base[:2])):
            cases.append(dict(payloads=[{'name':'variant','result':{'records':rows}}],contract=copy.deepcopy(c)))
        conflict=copy.deepcopy(base[0]); conflict['score']+=1
        cases.append(dict(payloads=[{'name':'variant','result':{'records':base+[conflict]}}],contract=copy.deepcopy(c)))
        if op=='remediation_plan':
            quiet=copy.deepcopy(base)
            for r in quiet: r['tags']=[]
            condition=copy.deepcopy(c); condition['only_if_blocking']=True
            cases.append(dict(payloads=[{'name':'variant','result':{'records':quiet}}],contract=condition))
    else:
        for seed in (700+spec['index']*3,901+spec['index']*5):
            p=fixture(op,seed)
            cases.append(dict(payloads=[p]+copy.deepcopy(original[1:]),contract=copy.deepcopy(c)))
        cases.append(dict(payloads=[empty(op)],contract=copy.deepcopy(c)))
        cases.append(dict(payloads=[invalid(op,spec['index']+77)],contract=copy.deepcopy(c)))
        bad=copy.deepcopy(fixture(op,spec['index']+51))
        # A second independent boundary beyond empty/one invalid field.
        if op.endswith('_evidence'):
            bad[0]['total']=0
        elif op=='weighted_intervals': bad['windows'][0]['end']=bad['windows'][0]['start']
        elif op=='capacity_assignment': bad['jobs'][0]['duration']=-1
        elif op=='critical_path': bad['nodes'][0]['deps']=['j5']  # j0 -> j2 -> j4? include explicit cycle below
        elif op=='event_decode': bad['events']=[dict(partition='p',offset=True,committed=True)]
        elif op=='settlement_decode': bad['events']=[dict(id='x',revision=0,ts=0,key='a',value=True)]
        elif op=='checkpoint_replay':
            bad['checkpoints']=[dict(partition='x',offset=0,epoch=2),dict(partition='x',offset=1,epoch=2)]
        elif op=='trace_correlation': bad['spans'][0]['parent']='missing'
        elif op=='log_compatibility': bad['lines']=['{invalid']
        elif op=='schema_compatibility': bad['new'][0]['type']='bytes'
        elif op=='event_windows':
            bad['events']=[dict(id='same',revision=1,ts=0,key='a',value=2),dict(id='same',revision=1,ts=0,key='a',value=3)]
        elif op=='dependency_impact': bad['edges']=[['','x']]
        elif op=='policy_precedence': bad['rules'][0]['priority']=True
        if op=='critical_path': bad['nodes'][5]['deps']=['j0']
        cases.append(dict(payloads=[bad],contract=copy.deepcopy(c)))
        if op=='capacity_assignment':
            infeasible=fixture(op,3)
            for worker in infeasible['workers']: worker['capacity']=0
            cases.append(dict(payloads=[infeasible],contract=copy.deepcopy(c)))
        if op=='weighted_intervals':
            cases.append(dict(payloads=[{'windows':[dict(id='a',start=0,end=1,value=0),dict(id='b',start=5,end=6,value=2)]}],contract=dict(c,cooldown=0)))
        if op=='critical_path':
            cases.append(dict(payloads=[{'nodes':[dict(id='a',duration=0,deps=[]),dict(id='b',duration=0,deps=[]),dict(id='c',duration=1,deps=['b','a'])]}],contract=copy.deepcopy(c)))
        if op=='event_windows':
            events=[dict(id='x',revision=2,ts=0,key='a',value=9),dict(id='x',revision=1,ts=0,key='a',value=1),dict(id='x',revision=1,ts=0,key='a',value=2)]
            cases.append(dict(payloads=[dict(events=events)],contract=copy.deepcopy(c)))
        if op=='checkpoint_replay':
            cp=[dict(partition='x',offset=2,epoch=2),dict(partition='x',offset=0,epoch=1),dict(partition='x',offset=1,epoch=1)]
            cases.append(dict(payloads=[dict(checkpoints=cp,events=[])],contract=copy.deepcopy(c)))
    return cases

def probes(workspace,spec,available,only=None):
    count=0
    for s in spec['specs']:
        if only and s['folder']!=only: continue
        cases=vectors(spec,s,available); wanted=[]
        for case in cases:
            try: wanted.append(dict(kind='value',value=evaluate(case['payloads'],case['contract'])))
            except ValueError: wanted.append(dict(kind='ValueError'))
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('probe.py')),str(workspace/s['folder']),spec['suite']],
            input=json.dumps({'cases':cases},ensure_ascii=False),capture_output=True,text=True,encoding='utf-8',timeout=45)
        assert result.returncode==0,'API probe failed: '+s['folder']+' '+result.stderr[-1200:]
        got=json.loads(result.stdout)
        assert len(got)==len(wanted)
        for i,(actual,expected) in enumerate(zip(got,wanted)):
            assert actual==expected,f"held-out API mismatch: {s['folder']} case {i}"
        count+=len(cases)
    return count

def verify(entry,workspace,api=True):
    workspace=Path(workspace).resolve(); specs=json.loads((ROOT/'_authoring/task_specs.json').read_text(encoding='utf-8'))
    seals=json.loads((ROOT/'verifier/protected_hashes.json').read_text(encoding='utf-8'))
    spec=specs[entry]; seal=seals[entry]
    integrity(workspace,seal)
    run=subprocess.run([sys.executable,str(workspace/'check.py')],cwd=workspace,capture_output=True,text=True,encoding='utf-8',timeout=180)
    # Verify even when candidate code fails, so tampering never hides behind a failure.
    integrity(workspace,seal,post=spec['suite']=='linux2')
    assert run.returncode==0,'local execution failed: '+run.stdout[-1000:]+' '+run.stderr[-1500:]
    available,expected=expected_outputs(spec)
    for rel,value in expected.items():
        path=workspace/rel
        assert path.is_file(),'missing output: '+rel
        raw=path.read_text(encoding='utf-8'); actual=json.loads(raw)
        assert actual==value,'incorrect output: '+rel
        canonical=json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
        assert raw==canonical,'noncanonical output: '+rel
    count=probes(workspace,spec,available) if api else 0
    integrity(workspace,seal,post=True)
    return dict(entry=entry,status='passed',output_count=len(expected),api_cases=count,protected_file_count=len(seal['initial'])+len(seal['generated']))

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--entry',required=True); parser.add_argument('--workspace',required=True)
    args=parser.parse_args()
    try:
        result=verify(args.entry,args.workspace)
    except Exception as exc:
        print(json.dumps(dict(status='failed',reason=str(exc)),ensure_ascii=False)); return 1
    print(json.dumps(result,ensure_ascii=False)); return 0

if __name__=='__main__': sys.exit(main())
