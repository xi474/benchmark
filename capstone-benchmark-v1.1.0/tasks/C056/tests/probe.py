"""One isolated candidate entrypoint invocation; author solutions are not imported."""
from pathlib import Path
import copy,importlib.util,json,os,sys,subprocess

job=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
output=Path(sys.argv[2]);work=Path(job['work']);sys.path.insert(0,str(work));os.chdir(work)
# The grader starts this interpreter as root, then irrevocably drops privileges
# before importing candidate code. Hidden tests remain root-only in /tests.
if 'uid' in job:
    os.setgroups([]);os.setgid(job['uid']);os.setuid(job['uid'])
try:
    spec=importlib.util.spec_from_file_location('solution',work/'solution.py')
    module=importlib.util.module_from_spec(spec);sys.modules['solution']=module;spec.loader.exec_module(module)
    payload=copy.deepcopy(job['payload']);before=copy.deepcopy(payload)
    if job['kind']=='transform':
        value=module.transform(payload);answer=dict(ok=True,value=value,input_unchanged=payload==before)
    else:
        inp=Path(job['input']);out=Path(job['output']);inp.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
        loaded=module.load_payload(str(inp));value=module.build_component(str(inp),str(out))
        stored=json.loads(out.read_text(encoding='utf-8'))
        answer=dict(ok=True,loaded=loaded,value=value,stored=stored)
    json.dumps(answer,allow_nan=False)
except Exception as exc:
    answer=dict(ok=False,error=type(exc).__name__,detail=str(exc)[:400])
output.write_text(json.dumps(answer,ensure_ascii=False,allow_nan=False),encoding='utf-8')
