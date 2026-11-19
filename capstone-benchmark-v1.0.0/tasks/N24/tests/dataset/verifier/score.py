"""Frozen A/B/D/P evaluation with 50% delivery bonus. No author solver imports."""
import argparse
import copy
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')

def protected(work,files):
    return [name for name,wanted in files.items() if not (work/name).is_file() or digest(work/name)!=wanted]

def snapshot(work,files):return {name:digest(work/name) for name in files}

def clean_copy(source,dest):
    shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc','outputs'))
    return dest

def pointer(value,path):
    for part in path.strip('/').split('/') if path.strip('/') else []:value=value[int(part)] if isinstance(value,list) else value[part]
    return value

def compare(ident,name,actual,wanted,context=None):
    if ident=='N15' and name=='archive':
        from semantic import archive_ok
        return archive_ok(actual,wanted)
    if ident=='N21' and name=='optimized_query':
        from semantic import sql_query_ok
        return sql_query_ok(actual)
    if ident=='N22' and name=='cleaned_repo':
        from semantic import git_clean_ok
        return git_clean_ok(actual,wanted)
    if ident=='N04' and name=='fallback_values':
        from semantic import sql_bool_ok
        return sql_bool_ok(actual,context or {})
    if ident=='N26' and name in ('distribution','distribution_report'):
        from semantic import distribution_ok
        return distribution_ok(name,actual,context or {})
    if ident=='N25' and name=='deployment_hook':
        from semantic import hook_ok
        return hook_ok(actual,context or {})
    return actual==wanted

def invoke(work,folder,contract,payload,kind,temp):
    job=temp/'job.json';result=temp/'result.json'
    write(job,dict(workspace=str(work),folder=folder,contract=contract,payload=payload,kind=kind))
    try:
        proc=subprocess.run([sys.executable,str(HERE/'probe.py'),'--job',str(job),'--out',str(result)],cwd=temp,capture_output=True,text=True,timeout=90,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        return read(result) if result.exists() else dict(ok=False,error='process',detail=proc.stderr[-500:])
    except subprocess.TimeoutExpired:return dict(ok=False,error='timeout')

def grade(package,ident,workspace):
    catalog=read(package/'verifier/catalog.json');row=catalog['tasks'][ident]
    assert digest(package/row['vectors'])==row['vectors_sha256'],'frozen vectors changed'
    registered={k:v for k,v in row.items() if k!='registry_sha256'}
    assert hashlib.sha256(json.dumps(registered,sort_keys=True,ensure_ascii=False).encode()).hexdigest()==row['registry_sha256'],'frozen registry changed'
    vectors=read(package/row['vectors']);workflow=read(package/row['entry']/'workspace/workflow.json')
    checks=[];violations=protected(workspace,row['protected'])
    def record(cid,category,passed,detail=''):
        checks.append(dict(id=cid,category=category,passed=bool(passed),detail=detail))
    with tempfile.TemporaryDirectory(prefix='medium30-score-') as td:
        temp=Path(td)
        for component in workflow['components']:
            name=component['name'];folder=component['folder'];contract=read(package/row['entry']/'workspace'/folder/'contract.json')
            cases=vectors['components'][name]
            for i,case in enumerate(cases):
                if violations:record(f'A/{name}/{i+1}','A',False,'integrity');continue
                run=temp/f'api-{name}-{i}';run.mkdir();work=clean_copy(workspace,run/'work');before=snapshot(work,row['protected'])
                answer=invoke(work,folder,contract,case['payload'],'transform',run)
                changed=protected(work,before)
                if changed:violations.extend(changed)
                passed=answer.get('ok') and answer.get('input_unchanged') and compare(ident,name,answer.get('value'),case['expected'],case['payload'])
                record(f'A/{name}/{i+1}','A',passed,'' if passed else answer.get('error','result_mismatch'))
            bundles=[]
            for i,case in enumerate(cases[:2]):
                if violations:bundles.append(False);continue
                run=temp/f'build-{name}-{i}';run.mkdir();work=clean_copy(workspace,run/'work');before=snapshot(work,row['protected'])
                answer=invoke(work,folder,contract,case['payload'],'bundle',run)
                changed=protected(work,before)
                if changed:violations.extend(changed)
                success=bool(answer.get('ok')) and all(answer.get('loads',[])) and answer.get('value')==answer.get('stored') and compare(ident,name,answer.get('value'),case['expected'],case['payload'])
                for path,item in contract.get('emit',{}).items():
                    emitted=answer.get('emitted',{}).get(path)
                    if ident=='N26':ok=compare(ident,'distribution',emitted,None,case['payload']) and emitted==answer.get('value')
                    elif ident=='N21':ok=compare(ident,'optimized_query',emitted,None,case['payload']) and emitted==answer.get('value')
                    elif ident=='N25':ok=compare(ident,'deployment_hook',emitted,None,case['payload']) and emitted==answer.get('value')
                    elif ident=='N15':
                        from semantic import archive_ok
                        ok=archive_ok({'tar':emitted,'rejected':case['expected']['rejected']},case['expected'])
                    elif ident=='N22' and name=='cleaned_repo':
                        from semantic import git_clean_ok
                        ok=git_clean_ok({**case['expected'],'bundle':emitted},case['expected'])
                    else:ok=emitted==pointer(case['expected'],item['pointer'])
                    success=success and ok
                bundles.append(success)
            record(f'B/{name}','B',len(bundles)==2 and all(bundles),'two_clean_builds_and_loaders')
        # D is one registered unit per component, one final integration unit,
        # plus each declared additional final artifact. All use fresh reruns.
        observed={c['name']:[] for c in workflow['components']};finals=[];extras={}
        for i,case in enumerate(vectors['integration']):
            if violations:break
            run=temp/f'integration-{i}';run.mkdir();work=clean_copy(workspace,run/'work')
            write(work/'inputs/request.json',case['input']);before=snapshot(work,row['protected'])
            try:
                proc=subprocess.run([sys.executable,'run_all.py'],cwd=work,capture_output=True,text=True,timeout=180,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
                report=read(work/'outputs/final_report.json') if proc.returncode==0 else {}
            except Exception:report={}
            changed=protected(work,before)
            if changed:violations.extend(changed)
            for c in workflow['components']:
                name=c['name'];contract=read(package/row['entry']/'workspace'/c['folder']/'contract.json')
                try:actual=read(work/contract['output'])
                except Exception:actual=None
                wanted=case['results'][name]
                observed[name].append(actual==report.get('results',{}).get(name) and compare(ident,name,actual,wanted,case['input']))
                for path,item in contract.get('emit',{}).items():
                    try:
                        p=work/path
                        if item['format']=='text':value=p.read_text(encoding='utf-8')
                        elif item['format']=='json':value=read(p)
                        elif item['format']=='ics':
                            from semantic import ics_record
                            value=ics_record(p.read_text(encoding='utf-8'))
                        elif item['format']=='base64':
                            import base64
                            value=base64.b64encode(p.read_bytes()).decode()
                        else:
                            import numpy as np
                            value=np.load(p,allow_pickle=False).tolist()
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
                    except Exception:ok=False
                    extras.setdefault(path,[]).append(ok)
            last=workflow['components'][-1]['name']
            finals.append(report.get('task')==ident and compare(ident,last,report.get('result'),case['results'][last],case['input']))
        count=len(vectors['integration'])
        for name,values in observed.items():record('D/'+name,'D',len(values)==count and all(values))
        record('D/final_report','D',len(finals)==count and all(finals))
        for c in workflow['components']:
            contract=read(package/row['entry']/'workspace'/c['folder']/'contract.json')
            for path in contract.get('emit',{}):
                values=extras.get(path,[]);record('D/artifact/'+path,'D',len(values)==count and all(values))
        public=False
        if not violations:
            run=temp/'public';run.mkdir();work=clean_copy(workspace,run/'work');before=snapshot(work,row['protected'])
            try:public=subprocess.run([sys.executable,'check.py'],cwd=work,capture_output=True,timeout=180,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}).returncode==0
            except Exception:pass
            changed=protected(work,before)
            if changed:violations.extend(changed)
        record('P/public_check','P',public)
    assert [x['id'] for x in checks]==row['check_ids'],'frozen verifier registry mismatch'
    integrity=not violations
    if not integrity:
        for check in checks:check['passed']=False;check['detail']='integrity_invalid'
    n=len(checks);k=sum(c['passed'] for c in checks);strict=integrity and all(c['passed'] for c in checks)
    a=[c for c in checks if c['category']=='A'];ka=sum(c['passed'] for c in a)
    reward=(Decimal(row['weight'])*(Decimal('0.5')*Decimal(k)/Decimal(n)+Decimal('0.5')*int(strict))) if integrity else Decimal(0)
    return dict(schema='benchmark.delivery-reward.v1',scoring_revision='delivery-bonus-50-v1',task=ident,status='scored' if integrity else 'invalid_submission',integrity_ok=integrity,integrity_violations=sorted(set(violations)),public_pass=integrity and public,strict_pass=strict,core_transform_passed=ka,core_transform_total=len(a),core_transform_case_pass_rate=ka/len(a) if a else None,passed_verifiers=k,total_verifiers=n,pass_ratio=k/n,all_checks_passed=strict,reward=float(reward.quantize(Decimal('.000001'),rounding=ROUND_HALF_UP)),max_reward=row['weight'],progress_reward=float(Decimal(row['weight'])*Decimal('.5')*Decimal(k)/Decimal(n)) if integrity else 0,delivery_bonus=row['weight']*.5*int(strict),checks=checks,robustness_registered=False,robustness_pass_ratio=None,full_spec_pass=None,registry_sha256=row['registry_sha256'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--task',required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--json-output',type=Path);p.add_argument('--reward-output',type=Path);args=p.parse_args()
    result=grade(args.package.resolve(),args.task,args.workspace.resolve())
    if args.json_output:write(args.json_output,result)
    if args.reward_output:
        args.reward_output.parent.mkdir(parents=True,exist_ok=True);args.reward_output.write_text(str(result['reward']),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['checks']},ensure_ascii=False))
