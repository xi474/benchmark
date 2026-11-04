"""Versioned partial reward; task sources and original strict verifiers remain untouched."""
from __future__ import annotations
import argparse,collections,copy,hashlib,json,math,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
from arithmetic import reward
import adapters
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def dump(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
def same(a,b):
    if type(a) in (int,float) and type(b) in (int,float):return math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-9)
    if type(a) is not type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b
def difference(a,b,path='$'):
    if type(a) is not type(b):return dict(path=path,actual_type=type(a).__name__,expected_type=type(b).__name__)
    if isinstance(a,dict):
        if a.keys()!=b.keys():return dict(path=path,actual_keys=list(a),expected_keys=list(b))
        for k in a:
            if not same(a[k],b[k]):return difference(a[k],b[k],path+'.'+k)
    elif isinstance(a,list):
        if len(a)!=len(b):return dict(path=path,actual_length=len(a),expected_length=len(b))
        for i,(x,y) in enumerate(zip(a,b)):
            if not same(x,y):return difference(x,y,f'{path}[{i}]')
    return dict(path=path,actual=str(a)[:240],expected=str(b)[:240])
def command(cmd,cwd,timeout=240):
    try:
        p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,encoding='utf-8',timeout=timeout)
        return dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
    except subprocess.TimeoutExpired:return dict(returncode=-1,stdout='',stderr='timeout')
def protected(w,row,post=False):
    errors=[]
    for rel,accepted in {**row['protected_initial'],**(row['protected_generated'] if post else {})}.items():
        p=w/rel
        if not p.is_file() or p.is_symlink() or w not in p.resolve().parents:errors.append('missing/unsafe '+rel)
        elif sha(p) not in accepted:errors.append('changed '+rel)
    if not post:
        for rel,accepted in row['protected_generated'].items():
            p=w/rel
            if p.exists() and (not p.is_file() or p.is_symlink() or sha(p) not in accepted):errors.append('changed generated '+rel)
    return errors
def check_digest(checks):return hashlib.sha256(json.dumps(checks,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def report(core,title):
    attention=[]
    for name,r in core['components'].items():
        if r.get('blocked') is True or any(r.get(k) is False for k in ['complete','checkout','committed','ok']) or any(bool(r.get(k)) for k in ['unavailable','missing','conflicts','unreachable']):attention.append(name)
    return dict(title=title,component_count=len(core['components']),sha256=hashlib.sha256(canonical(core).encode()).hexdigest(),attention=sorted(attention))

def evaluate(check,w,root_run):
    kind=check['kind']
    if kind in ('api','io'):
        packet={k:copy.deepcopy(check[k]) for k in ['kind','folder','suite','case','flavor']};packet['workspace']=str(w)
        try:p=subprocess.run([sys.executable,str(HERE/'probe.py')],input=json.dumps(packet,ensure_ascii=False),cwd=w,capture_output=True,text=True,encoding='utf-8',timeout=45)
        except subprocess.TimeoutExpired:return False,'timeout'
        if p.returncode:return False,'probe execution error: '+p.stderr[-600:]
        try:got=json.loads(p.stdout)
        except ValueError:return False,'invalid probe output'
        if kind=='io':return bool(got.get('kind')=='io' and got.get('passed')),got.get('details',got)
        valid=same(got,check['expected']) if check['flavor']=='medium' else got==check['expected']
        return valid,'matched' if valid else difference(got,check['expected'])
    if kind in ('output','report'):
        p=w/check['path']
        if not p.is_file() or p.is_symlink():return False,'missing/unsafe output'
        try:
            source=p.read_text(encoding='utf-8');actual=json.loads(source)
            expected=report(json.loads((w/'outputs/core_manifest.json').read_text(encoding='utf-8')),check['title']) if kind=='report' else check['expected']
            if check['flavor']=='medium':passed=same(actual,expected) and source==dump(actual)
            else:passed=actual==expected and source==dump(expected)
            return passed,'matched' if passed else (difference(actual,expected) if not same(actual,expected) else 'noncanonical serialization')
        except (ValueError,KeyError,TypeError,OSError):return False,'unreadable/invalid output'
    if kind=='focused':
        folder=w/check['folder'];p=command([sys.executable,str(HERE/'focused_probe.py'),str(w),check['folder']],folder)
        return p['returncode']==0,p['stderr'][-600:] or p['stdout'][-300:]
    if kind=='root':return root_run['returncode']==0,root_run['stderr'][-600:] or root_run['stdout'][-300:]
    raise ValueError('unknown verifier kind')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--benchmark-root',type=Path,required=True);parser.add_argument('--task',required=True);parser.add_argument('--workspace',type=Path);parser.add_argument('--describe',action='store_true');parser.add_argument('--scratch',type=Path);parser.add_argument('--json-output',type=Path);parser.add_argument('--reward-output',type=Path);args=parser.parse_args()
    benchmark=args.benchmark_root.resolve();catalog_path=HERE/'catalog.json';catalog=json.loads(catalog_path.read_text(encoding='utf-8')) if catalog_path.is_file() else {};row=catalog.get('tasks',{}).get(args.task)
    if row is None:
        if not args.describe:raise ValueError('unknown task')
        row=json.loads(sys.stdin.read())
    checks=adapters.checks(benchmark,row);assert checks and len({c['id'] for c in checks})==len(checks)
    if args.describe:
        print(json.dumps(dict(verifiers=[{k:c[k] for k in ['id','category','kind']} for c in checks],checks_sha256=check_digest(checks)),ensure_ascii=False));return 0
    if len(checks)!=row['verifier_count'] or check_digest(checks)!=row['checks_sha256']:raise ValueError('trusted tests changed; rebuild/version the catalog')
    policy=json.loads((HERE/'policy.json').read_text(encoding='utf-8'));source=args.workspace.resolve();started=time.monotonic();violations=protected(source,row);results=[];execution={}
    if not violations:
        if any(p.is_symlink() for p in source.rglob('*')):violations=['symbolic link in submission']
    if not violations:
        with tempfile.TemporaryDirectory(prefix='reward-v2-',dir=args.scratch) as temp:
            work=Path(temp)/'workspace'
            shutil.copytree(source,work,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            output=work/'outputs'
            if output.exists():
                if output.resolve().parent!=work.resolve():raise ValueError('unsafe scratch outputs')
                shutil.rmtree(output)
            if (work/'materialize.py').is_file():execution['materialize']=command([sys.executable,str(work/'materialize.py')],work)
            execution['root']=command([sys.executable,str(work/'check.py')],work)
            for c in checks:
                try:passed,detail=evaluate(c,work,execution['root'])
                except Exception as exc:passed,detail=False,type(exc).__name__+': '+str(exc)[:400]
                results.append(dict(id=c['id'],category=c['category'],passed=passed,detail=detail))
            violations=protected(work,row,post=True)
    if not results:results=[dict(id=c['id'],category=c['category'],passed=False,detail='blocked by integrity') for c in checks]
    passed=sum(x['passed'] for x in results);score=reward(passed,len(checks),row['difficulty'],policy,integrity=not violations);categories={}
    for x in results:
        categories.setdefault(x['category'],dict(passed=0,total=0));categories[x['category']]['total']+=1;categories[x['category']]['passed']+=int(x['passed'])
    result=dict(schema='benchmark.partial-reward.v2',task=args.task,difficulty=row['difficulty'],status='invalid_submission' if violations else 'scored',policy_version=policy['version'],policy_sha256=sha(HERE/'policy.json'),catalog_sha256=sha(catalog_path),checks_sha256=row['checks_sha256'],**score,categories=categories,integrity_violations=violations,checks=results,root_execution_succeeded=execution.get('root',{}).get('returncode')==0,elapsed_seconds=round(time.monotonic()-started,3),model_requests=0)
    if args.json_output:args.json_output.parent.mkdir(parents=True,exist_ok=True);args.json_output.write_text(dump(result),encoding='utf-8')
    if args.reward_output:args.reward_output.parent.mkdir(parents=True,exist_ok=True);args.reward_output.write_text(f'{score["reward"]:.6f}\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['checks']},ensure_ascii=False,allow_nan=False));return 0
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:print(json.dumps(dict(status='grader_error',error=type(exc).__name__+': '+str(exc)),ensure_ascii=False));sys.exit(2)
