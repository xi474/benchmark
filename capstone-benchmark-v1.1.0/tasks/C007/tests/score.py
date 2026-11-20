"""Frozen 50% delivery-bonus scoring: core cases, independent builds, CLI and public check."""
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
import argparse,hashlib,itertools,json,math,os,shutil,signal,subprocess,sys,tempfile,time

HERE=Path(__file__).resolve().parent
UIDS=itertools.count(50000)
USED_UIDS=set()
GRADING_DEADLINE=float('inf')
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')

def equal(a,b,tol):
    if isinstance(b,dict) and b.get("__clustering_truth__"):
        from quality import accepted
        return accepted(a,b)
    if isinstance(a,bool) or isinstance(b,bool):return type(a)==type(b) and a==b
    if isinstance(a,(float,int)) and isinstance(b,(float,int)):
        absolute=tol.get('atol',0) if isinstance(tol,dict) else tol
        relative=tol.get('rtol',0) if isinstance(tol,dict) else 0
        return math.isfinite(a) and math.isfinite(b) and abs(a-b)<=absolute+relative*abs(b)
    if isinstance(a,dict) and isinstance(b,dict):return a.keys()==b.keys() and all(equal(a[k],b[k],tol) for k in a)
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(equal(x,y,tol) for x,y in zip(a,b))
    return type(a)==type(b) and a==b

def clean(source,dest):
    shutil.copytree(source,dest,symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','outputs','.git'))
    return dest

def protected(work,registry):
    return [name for name,wanted in registry.items() if not (work/name).is_file() or sha(work/name)!=wanted]

def own_tree(folder,uid):
    assert sys.platform=='linux' and os.geteuid()==0,'Isolated evaluation requires Linux root supervisor'
    USED_UIDS.add(uid)
    for path in [folder]+list(folder.rglob('*')):
        if not path.is_symlink():os.chown(path,uid,uid)
    os.chmod(folder,0o700)

def demote(uid):
    def apply():os.setgroups([]);os.setgid(uid);os.setuid(uid)
    return apply

def cleanup_candidate_processes():
    # Descendants must not outlive scoring and race the supervisor's final logs.
    for _ in range(4):
        found=[]
        for path in Path('/proc').iterdir():
            if not path.name.isdigit():continue
            try:
                lines=(path/'status').read_text().splitlines()
                uid=int(next(line for line in lines if line.startswith('Uid:')).split()[1])
                if uid in USED_UIDS:found.append(int(path.name))
            except (OSError,StopIteration):continue
        if not found:return
        for pid in found:
            try:os.kill(pid,signal.SIGKILL)
            except ProcessLookupError:pass
        time.sleep(.02)
    # A remaining zombie cannot execute or write; the container reaps it on exit.

def invoke(work,payload,kind,folder):
    if time.monotonic()>=GRADING_DEADLINE:return dict(ok=False,error='verifier_budget_exhausted')
    folder.mkdir();job=folder/'job.json';answer=folder/'answer.json';uid=next(UIDS)
    save(job,dict(work=str(work),payload=payload,kind=kind,uid=uid,input=str(folder/'fresh-input.json'),output=str(folder/'fresh-output.json')))
    own_tree(work,uid);own_tree(folder,uid)
    try:
        proc=subprocess.run([sys.executable,str(HERE/'probe.py'),str(job),str(answer)],cwd=folder,
            capture_output=True,text=True,timeout=min(120,max(1,GRADING_DEADLINE-time.monotonic())),env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        return read(answer) if answer.exists() else dict(ok=False,error='process',detail=proc.stderr[-400:])
    except subprocess.TimeoutExpired:return dict(ok=False,error='timeout')

def grade(workspace,registry,cases):
    global GRADING_DEADLINE
    GRADING_DEADLINE=time.monotonic()+1500
    checks=[];violations=protected(workspace,registry['protected']);tol=registry.get('tolerance',0)
    def record(name,kind,ok,detail=''):checks.append(dict(id=name,category=kind,passed=bool(ok),detail=detail))
    def fresh(root,name):return clean(workspace,root/name)
    with tempfile.TemporaryDirectory(prefix='hard31-score-') as tmp:
        root=Path(tmp);os.chmod(root,0o711)
        for i,case in enumerate(cases):
            if time.monotonic()>=GRADING_DEADLINE:
                record('A/'+case['id'],'A',False,'verifier_budget_exhausted');continue
            work=fresh(root,f'core-{i}');a=invoke(work,case['input'],'transform',root/f'probe-core-{i}')
            changes=protected(work,registry['protected']);violations+=changes
            record('A/'+case['id'],'A',not violations and a.get('ok') and a.get('input_unchanged')
                   and equal(a.get('value'),case['expected'],tol),a.get('error',''))
        for i,case in enumerate([cases[0],cases[-1]]):
            if time.monotonic()>=GRADING_DEADLINE:
                record(f'B/clean-build-{i+1}','B',False,'verifier_budget_exhausted');continue
            work=fresh(root,f'bundle-{i}');a=invoke(work,case['input'],'bundle',root/f'probe-build-{i}')
            changes=protected(work,registry['protected']);violations+=changes
            record(f'B/clean-build-{i+1}','B',not violations and a.get('ok')
                and equal(a.get('loaded'),case['input'],0) and equal(a.get('value'),case['expected'],tol)
                and equal(a.get('stored'),case['expected'],tol),a.get('error',''))
        for i,case in enumerate([cases[0],cases[-1]]):
            if time.monotonic()>=GRADING_DEADLINE:
                record(f'D/cli-artifact-{i+1}','D',False,'verifier_budget_exhausted');continue
            work=fresh(root,f'cli-{i}')
            save(work/'public_input.json',case['input'])
            # The changed test input is sanctioned on this private evaluator copy only.
            before={k:sha(work/k) for k in registry['protected']}
            uid=next(UIDS);own_tree(work,uid)
            try:
                proc=subprocess.run([sys.executable,'run_all.py','--input','public_input.json','--output','outputs/result.json'],cwd=work,capture_output=True,text=True,timeout=min(180,max(1,GRADING_DEADLINE-time.monotonic())),
                    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},preexec_fn=demote(uid))
                value=read(work/'outputs/result.json') if proc.returncode==0 else None
                changed=protected(work,before);violations+=changed
                record(f'D/cli-artifact-{i+1}','D',not violations and proc.returncode==0 and equal(value,case['expected'],tol))
            except Exception as exc:record(f'D/cli-artifact-{i+1}','D',False,type(exc).__name__)
        work=fresh(root,'public')
        cmd=[sys.executable,'public_check.py'] if (work/'public_check.py').exists() else [sys.executable,'run_all.py','--check']
        uid=next(UIDS);own_tree(work,uid)
        try:
            if time.monotonic()>=GRADING_DEADLINE:raise subprocess.TimeoutExpired(cmd,0)
            proc=subprocess.run(cmd,cwd=work,capture_output=True,text=True,timeout=min(180,max(1,GRADING_DEADLINE-time.monotonic())),
                 env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},preexec_fn=demote(uid))
            violations+=protected(work,registry['protected'])
            public=proc.returncode==0 and not violations
        except Exception:public=False
        record('P/public-check','P',public)
    cleanup_candidate_processes()
    integrity=not violations
    passed=sum(c['passed'] for c in checks) if integrity else 0
    strict=integrity and all(c['passed'] for c in checks)
    fraction=Decimal(passed)/Decimal(len(checks));maximum=Decimal(str(registry['max_reward']))
    normalized=(Decimal('.5')*fraction+Decimal('.5')*Decimal(int(strict))) if integrity else Decimal(0)
    reward=(maximum*normalized).quantize(Decimal('.00000001'),rounding=ROUND_HALF_UP)
    core=[c for c in checks if c['category']=='A'];cp=sum(c['passed'] for c in core) if integrity else 0
    return dict(task=registry['task'],scoring_revision='delivery-bonus-50-v1',strict_pass=bool(strict),public_pass=bool(public),
        integrity_pass=integrity,protected_violations=sorted(set(violations)),passed_verifiers=passed,total_verifiers=len(checks),
        core_transform_cases_passed=cp,core_transform_cases_total=len(core),core_transform_case_pass_rate=cp/len(core),
        reward=float(reward),max_reward=float(maximum),normalized_reward=float(normalized),checks=checks,
        note='上游原题独立评分；本记录仅对应冻结的改编版。')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--registry',type=Path,required=True)
    p.add_argument('--cases',type=Path,required=True);p.add_argument('--json-output',type=Path,required=True);p.add_argument('--reward-output',type=Path,required=True)
    args=p.parse_args();reg=read(args.registry);assert sha(args.cases)==reg['cases_sha256']
    os.chmod(HERE,0o700)
    assert HERE.stat().st_mode&0o077==0,'Hidden test directory is not private; evaluator must fail closed'
    result=grade(args.workspace,reg,read(args.cases));save(args.json_output,result)
    args.reward_output.parent.mkdir(parents=True,exist_ok=True);args.reward_output.write_text(str(result['normalized_reward'])+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['task','strict_pass','reward','max_reward','passed_verifiers','total_verifiers']}))
