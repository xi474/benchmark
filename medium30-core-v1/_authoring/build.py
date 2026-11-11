"""Build versioned task packages; all author solutions stay outside agent inputs."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'authoring'))
from blueprints import TASKS
from references import solve
from oracles import expected
from runtime import pointer

DEST=ROOT/'release/medium30-core-v1'
FOLDERS={'reasoning4':'engines','multistage4':'stages','context8':'packages','linux2':'products'}
DESIGN_FILE=ROOT/'authoring/candidate_designs.json'
if not DESIGN_FILE.exists():DESIGN_FILE=ROOT.parent/'new30-asci-candidates-20261109/candidates.json'
DESIGNS={x['id']:x for x in json.loads(DESIGN_FILE.read_text(encoding='utf-8'))['tasks']}

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8',newline='\n')
def dump(path,data):write(path,json.dumps(data,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

STUB='''"""Implement the business transform. I/O helpers are supplied and editable here."""
from pathlib import Path
import json
from runtime import build

def transform(payload, contract):
    raise NotImplementedError("Implement according to SPEC.md")

def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def build_component(root, contract):
    return build(root, contract, transform)
'''

def transcript(task,payload):
    blobs={'inputs/request.json':copy.deepcopy(payload)};trace={};cases={}
    for c in task['components']:
        p={k:pointer(blobs[b.partition('#')[0]],b.partition('#')[2]) for k,b in c['bindings'].items()}
        result=solve(c['op'],copy.deepcopy(p),c)
        trace[c['name']]=result;cases[c['name']]=dict(payload=p,expected=result)
        blobs['outputs/'+c['name']+'.json']=result
    if task['id']=='N26':
        import math
        values=trace['distribution'];n=payload['n']
        assert len(values)==n and min(values)>0 and abs(math.fsum(values)-1)<=1e-5
        assert abs(math.fsum(x*math.log(x*n) for x in values)-payload['targets']['forward'])<=.001
        assert abs(math.fsum(math.log(1/(x*n)) for x in values)/n-payload['targets']['backward'])<=.001
    else:assert trace[task['components'][-1]['name']]==expected(task['oracle'],payload),(task['id'],'independent final oracle disagreement')
    return dict(input=payload,results=trace),cases

def main(ids):
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/'review').mkdir(exist_ok=True)
    shutil.copytree(ROOT/'verifier',DEST/'verifier',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copyfile(ROOT/'authoring/runtime.py',DEST/'verifier/fixture_runtime.py')
    catalog=json.loads((DEST/'verifier/catalog.json').read_text(encoding='utf-8')) if (DEST/'verifier/catalog.json').exists() else {'schema':'medium30.registry.v1','scoring_revision':'delivery-bonus-50-v1','tasks':{}}
    entries=[x for x in json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))['tasks'] if x['id'] not in ids] if (DEST/'manifest.json').exists() else []
    for ident in ids:
        task=TASKS[ident];design=DESIGNS[ident];style=design['style'];entry='tasks/'+style+'/'+task['slug'];folder=DEST/entry;work=folder/'workspace'
        workflow=dict(id=ident,style=style,components=[])
        vectors=dict(components={c['name']:[] for c in task['components']},integration=[])
        for item in task['inputs']:
            whole,parts=transcript(task,item);vectors['integration'].append(whole)
            for name,value in parts.items():vectors['components'][name].append(value)
        for component in task['components']:
            component=copy.deepcopy(component);name=component['name'];loc=FOLDERS[style]+'/'+name
            workflow['components'].append(dict(name=name,folder=loc))
            component.update(output=component.pop('output_file','outputs/'+name+'.json'),component=name,task=ident)
            assert component['output'] not in component.get('emit',{}),'component/artifact output path collision'
            dump(work/loc/'contract.json',component)
            write(work/loc/'engine.py',STUB)
            write(work/loc/'SPEC.md',f"# {name}\n\n{component['spec']}\n\n## API 与文件契约\n\n`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。\n\n仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。\n")
        dump(work/'workflow.json',workflow);dump(work/'inputs/request.json',task['inputs'][0])
        shutil.copyfile(ROOT/'authoring/runtime.py',work/'runtime.py')
        write(work/'run_all.py',"from pathlib import Path\nfrom runtime import execute\nif __name__=='__main__': execute(Path(__file__).resolve().parent)\n")
        last=task['components'][-1]['name']
        dump(work/'public_expected.json',vectors['integration'][0]['results'][last])
        write(work/'check.py',"from pathlib import Path\nfrom runtime import execute,read\nroot=Path(__file__).resolve().parent\nreport=execute(root)\nassert report['result']==read(root/'public_expected.json'),'Public example mismatch'\nprint('PUBLIC PASS')\n")
        if ident=='N22':
            public=copy.deepcopy(vectors['integration'][0]['results'][last]);public['secret_sha256']=hashlib.sha256(public.pop('secret').encode()).hexdigest();dump(work/'public_expected.json',public)
            write(work/'check.py',"import hashlib\nfrom pathlib import Path\nfrom runtime import execute,read\nroot=Path(__file__).resolve().parent\nvalue=execute(root)['result'];value['secret_sha256']=hashlib.sha256(value.pop('secret').encode()).hexdigest()\nassert value==read(root/'public_expected.json')\nprint('PUBLIC PASS')\n")
        if ident=='N26':
            write(work/'check.py',"import math\nfrom pathlib import Path\nimport numpy as np\nfrom runtime import execute,read\nroot=Path(__file__).resolve().parent\nreport=execute(root);p=np.load(root/'outputs/dist.npy',allow_pickle=False);request=read(root/'inputs/request.json');n=request['n']\nassert p.ndim==1 and p.size==n and np.isfinite(p).all() and p.min()>0 and abs(math.fsum(p)-1)<=1e-5\nassert abs(math.fsum(float(x)*math.log(float(x)*n) for x in p)-request['targets']['forward'])<=.001\nassert abs(math.fsum(math.log(1/(float(x)*n)) for x in p)/n-request['targets']['backward'])<=.001\nassert report['result']['meets_target']\nprint('PUBLIC PASS')\n")
        if style=='linux2':write(work/'materialize.py',"# Only creates directories; never overwrites submitted modules.\nfrom pathlib import Path\nroot=Path(__file__).resolve().parent\n(root/'outputs').mkdir(exist_ok=True)\n")
        notes='\n'.join(f"- `{c['folder']}`：{next(x['spec'] for x in task['components'] if x['name']==c['name'])}" for c in workflow['components'])
        write(work/'README.md',f"# {ident} {design['title']}\n\n{design['goal']}\n\n## 本版输入与业务范围\n\n{task.get('scope',design['adaptation'])}\n\n{notes}\n\n## 运行\n\n仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。\n\n`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。\n\n公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。\n")
        write(folder/'TASK.md',f"# {ident} {design['title']}\n\n在 workspace 内按 README.md、各 SPEC.md 与 contract.json 完成组件。{design['goal']}\n\n只实现公开业务范围，使用提供的正常输入与文件依赖；不要求额外通用边界防御。必须确保 check.py 成功、组件可从干净输入独立构建、最终产物语义正确，不修改受保护文件。\n")
        vecpath='verifier/vectors/'+ident+'.json';dump(DEST/vecpath,vectors)
        protected={p.relative_to(work).as_posix():sha(p) for p in work.rglob('*') if p.is_file() and p.name!='engine.py'}
        checkids=[]
        for c in workflow['components']:
            name=c['name'];checkids.extend(f'A/{name}/{i+1}' for i in range(len(vectors['components'][name])));checkids.append('B/'+name)
        checkids.extend('D/'+c['name'] for c in workflow['components']);checkids.append('D/final_report')
        for c in task['components']:checkids.extend('D/artifact/'+p for p in c.get('emit',{}))
        checkids.append('P/public_check')
        registry=dict(entry=entry,vectors=vecpath,weight=2,check_ids=checkids,protected=protected,vectors_sha256=sha(DEST/vecpath))
        registry['registry_sha256']=hashlib.sha256(json.dumps(registry,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        catalog['tasks'][ident]=registry
        entries.append(dict(id=ident,title=design['title'],entry=entry,style=style,design_difficulty='M',empirical_difficulty=None,component_count=len(task['components']),source_ids=[s['source_id'] for s in design['sources']]))
    entries.sort(key=lambda x:x['id'])
    dump(DEST/'verifier/catalog.json',catalog)
    dump(DEST/'manifest.json',dict(dataset='medium30-core-v1',version='1.0.0-pre1',status='author_qa_pending',tasks=entries,scoring_revision='delivery-bonus-50-v1',core_only=True,model_runs=0))
    dump(DEST/'review/source_annotations.json',[dict(id=i,**{k:DESIGNS[i][k] for k in ['title','sources','asci','axis_evidence','minimum_counterexample','excluded_from_core','duplicate_distinction']}) for i in [e['id'] for e in entries]])
    print('BUILT',len(entries),'tasks,',sum(t['component_count'] for t in entries),'components')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ids',nargs='*');a=p.parse_args();main(a.ids or sorted(TASKS))
