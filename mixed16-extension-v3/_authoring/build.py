from __future__ import annotations
import hashlib
import json
import shutil
import sys
from pathlib import Path
from specification import SCENARIOS, RULES, fixture

HERE=Path(__file__).resolve().parent
DEST=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else HERE.parent/'mixed16-v2-staging'

def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(s,encoding='utf-8',newline='\n')
def dump(p,v): write(p,json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

SMOKE='''import json,sys,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[ROOT_DEPTH]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from model import load_payload
from transform import transform
from render import build_component
C=json.loads(Path(__file__).with_name('contract.json').read_text(encoding='utf-8'))
payloads=[load_payload(ROOT/p) for p in C['inputs']]
before=copy.deepcopy(payloads)
result=transform(payloads,C)
assert payloads==before, 'must not mutate inputs'
assert isinstance(result,dict) and set(result)=={'name','result'}
assert result['name']==C['name'] and isinstance(result['result'],dict)
assert build_component(ROOT,Path(__file__).with_name('contract.json'))==result
out=json.loads((ROOT/C['output']).read_text(encoding='utf-8'))
assert out==result, 'output must match function result'
print('MODULE_OK',C['name'])
'''

INTEGRATE='''import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def contracts():
    return sorted(p for p in ROOT.rglob('contract.json') if 'outputs' not in p.relative_to(ROOT).parts)
def write(path,data):
    p=ROOT/path; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\\n',encoding='utf-8')
def main():
    domain_mode=len(sys.argv)>1 and sys.argv[1]=='domains'
    selected=[p for p in contracts() if not domain_mode or p.parent.parent.name=='domains']
    if not selected: raise ValueError('no component contracts')
    values={}
    for p in selected:
        c=json.loads(p.read_text(encoding='utf-8'))
        value=json.loads((ROOT/c['output']).read_text(encoding='utf-8'))
        if value['name']!=c['name']: raise ValueError('component mismatch')
        values[c['name']]=value['result']
    if domain_mode:
        records={}
        for result in values.values():
            for r in result['records']:
                key=(r['source'],r['id'])
                if key in records and records[key]!=r: raise ValueError('source/id conflict')
                records[key]=r
        write('outputs/domain_core.json',{'name':'domain_core','result':{'records':sorted(records.values(),key=lambda r:(r['source'],r['id']))}})
    else: write('outputs/core_manifest.json',{'components':dict(sorted(values.items()))})
if __name__=='__main__': main()
'''

CHECK='''import json,subprocess,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
    out=ROOT/'outputs'
    if out.is_symlink(): raise ValueError('outputs must not be a symlink')
    if out.exists(): shutil.rmtree(out)
    if (ROOT/'materialize.py').exists(): subprocess.run([sys.executable,str(ROOT/'materialize.py')],cwd=ROOT,check=True,timeout=20)
    for name in ['run_all.py','final_report.py']:
        assert (ROOT/name).is_file(), 'missing implementation: '+name
    subprocess.run([sys.executable,str(ROOT/'run_all.py')],cwd=ROOT,check=True,timeout=120)
    contracts=sorted(ROOT.rglob('contract.json'))
    assert contracts, 'no contracts'
    for path in contracts:
        c=json.loads(path.read_text(encoding='utf-8'))
        value=json.loads((ROOT/c['output']).read_text(encoding='utf-8'))
        assert set(value)=={'name','result'} and value['name']==c['name'] and isinstance(value['result'],dict)
        subprocess.run([sys.executable,str(path.with_name('check_module.py'))],cwd=path.parent,check=True,timeout=20)
    report=json.loads((ROOT/'outputs/final_report.json').read_text(encoding='utf-8'))
    assert report['component_count']==len(contracts)
    assert len(report['sha256'])==64 and isinstance(report['attention'],list)
    print('LOCAL_CHECKS_PASSED; official scoring requires the external verifier')
if __name__=='__main__': main()
'''

MODEL='''import json
def load_payload(path):
    data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,(dict,list)): raise ValueError('expected JSON object or array')
    return data
'''

RENDER='''import json
from pathlib import Path
from model import load_payload
from transform import transform
def build_component(root,contract_path):
    c=load_payload(contract_path)
    return transform([load_payload(root/p) for p in c['inputs']],c)
if __name__=='__main__':
    cp=Path(__file__).with_name('contract.json'); root=Path(__file__).resolve().parents[ROOT_DEPTH]
    c=load_payload(cp); result=build_component(root,cp)
    out=root/c['output']; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\\n',encoding='utf-8')
'''

def contract(name,op,deps,seed):
    c=dict(name=name,operation=op,inputs=deps,output=f'outputs/{name}.json',threshold=11)
    if op.endswith('_evidence'): c.update(offset=seed%3-1,sla=7+seed%5)
    if op=='weighted_intervals': c.update(cooldown=seed%3)
    if op=='risk_ranking': c.update(limit=10+seed%3)
    if op=='review_balance': c.update(reviewers=['audit-a','audit-b','audit-c'])
    if op=='remediation_plan': c.update(only_if_blocking=False)
    if op=='event_windows': c.update(window_size=[30,60,90][seed%3])
    return c

def make_specs(suite,names,views,shape,index):
    from strengthening import enhanced_specs
    enhanced=enhanced_specs(suite,index)
    if enhanced is not None: return enhanced
    specs=[]; inputs={}
    def component(folder,name,op,deps=None):
        if deps is None:
            rel=f'inputs/{name}.json'; inputs[rel]=fixture(op,100+index*17+len(specs)); deps=[rel]
        c=contract(name,op,deps,100+index*17+len(specs))
        specs.append(dict(folder=f'{folder}/{name}' if folder else name,contract=c))
        return c['output']
    if suite=='multistage4':
        ops=[['lag_evidence','failure_evidence','integrity_evidence'],['failure_evidence','lag_evidence','integrity_evidence'],['failure_evidence','integrity_evidence','lag_evidence'],['integrity_evidence','lag_evidence','failure_evidence']][shape]
        sources=[component('domains',n,op) for n,op in zip(names,ops)]
        if shape==0:
            for n,op in zip(views,['risk_ranking','review_balance','remediation_plan']): component('views',n,op,['outputs/domain_core.json'])
        elif shape==1:
            a=component('views',views[0],'risk_ranking',sources[:1]); b=component('views',views[1],'review_balance',sources[:1])
            component('views',views[2],'remediation_plan',sources[1:]+[a,b])
        elif shape==2:
            a=component('views',views[0],'risk_ranking',sources[:2]); b=component('views',views[1],'review_balance',sources[2:])
            component('views',views[2],'remediation_plan',[a,b]); specs[-1]['contract']['only_if_blocking']=True
        else:
            a=component('views',views[0],'risk_ranking',sources[:1]); b=component('views',views[1],'review_balance',[a])
            component('views',views[2],'remediation_plan',sources[1:]+[b])
    elif suite=='reasoning4':
        if shape==0:
            a=component('engines',names[0],'weighted_intervals'); b=component('engines',names[1],'capacity_assignment')
            rel=f'inputs/{names[2]}.json'; inputs[rel]=fixture('critical_path',index+20)
            component('engines',names[2],'critical_path',[rel,b])
        elif shape==1:
            a=component('engines',names[0],'weighted_intervals'); b=component('engines',names[1],'critical_path')
            rel=f'inputs/{names[2]}.json'; inputs[rel]=fixture('capacity_assignment',index+20)
            component('engines',names[2],'capacity_assignment',[rel,a,b])
        elif shape==2:
            a=component('engines',names[0],'weighted_intervals')
            rel=f'inputs/{names[1]}.json'; inputs[rel]=fixture('capacity_assignment',index+20)
            component('engines',names[1],'capacity_assignment',[rel,a])
            component('engines',names[2],'critical_path')
        else:
            for n,op in zip(names,['weighted_intervals','capacity_assignment','critical_path']): component('engines',n,op)
    elif suite=='context8':
        if shape==0:
            a=component('',names[0],'settlement_decode'); component('',names[1],'event_windows',[a]); component('',names[2],'trace_correlation')
        elif shape==1:
            for n,op in zip(names,['schema_compatibility','trace_correlation','log_compatibility']): component('',n,op)
        elif shape==2:
            a=component('',names[0],'event_decode'); component('',names[1],'checkpoint_replay',[a]); component('',names[2],'log_compatibility')
        else:
            for n,op in zip(names,['schema_compatibility','event_windows','trace_correlation']): component('',n,op)
    else:
        ops=[['dependency_impact','policy_precedence','event_windows'],['dependency_impact','checkpoint_replay','event_windows'],['log_compatibility','event_windows','policy_precedence'],['dependency_impact','policy_precedence','trace_correlation']][shape]
        for n,op in zip(names,ops): component('products',n,op)
    return specs,inputs

def component_files(spec,suite):
    folder=spec['folder']; depth=len(Path(folder).parts)
    files={'contract.json':json.dumps(spec['contract'],ensure_ascii=False,indent=2)+'\n','check_module.py':SMOKE.replace('ROOT_DEPTH',str(depth))}
    if suite=='context8':
        files['__init__.py']=''
        files['parser.py']='''from .transform import transform
def parse(payloads,contract):
    """Stable package interface; payloads follows contract.inputs order."""
    return transform(payloads,contract)
'''
        files['transform.py']='''def transform(payloads,contract):
    raise NotImplementedError('repair compatibility and algorithm semantics')
'''
    if suite=='linux2':
        for module in ('model','transform','render'):
            files[module+'.py']=f"raise NotImplementedError('implement {module}.py')\n"
    return files

def readme(suite,name,title,goal,specs):
    lines=[f'# {title}',goal+'。本任务使用 Python 标准库，必须由输入重新计算，不能硬编码结果。',
      '## 不可修改文件','README.md、TASK.md、check.py、integrate.py、inputs/、任何 contract.json 和 check_module.py 不可修改。context 包的 __init__.py、parser.py 是稳定接口，也不可修改。linux 任务还保护 materialize.py 及其物化的输入、契约和局部检查。仅实现/修复各组件 model.py、transform.py、render.py，以及根 run_all.py、final_report.py；可添加私有辅助模块。',
      '## 组件接口',
      '契约字段顺序统一为 name、operation、inputs、output、threshold，再列算法参数。inputs 是必要文件接口，执行依赖需从现有接口中推导；没有计划 DAG、调度标签或隐藏的完整任务计划。所有组件输出统一封装 {"name":契约name,"result":算法结果对象}，下面的输出 schema 均指 result。JSON 采用 UTF-8、sort_keys=True、两空格缩进、末尾换行，禁止非有限值。',
      '- model.load_payload(path:Path)：读取 JSON 对象或数组，其他顶层类型或非法 JSON 抛 ValueError。字段验证在 transform 中完成。',
      '- transform.transform(payloads:list, contract:dict)：按 inputs 顺序接收已读取的数组或对象，返回上述封装；若输入为另一个组件封装，读取其 result。不得修改 payloads 或 contract。所有未声明的缺字段、非法类型、冲突均抛 ValueError；bool 不能作为整数或数值。',
      '- render.build_component(root:Path, contract_path:Path)：读取契约与全部输入，调用 transform 并返回封装；执行 python3 <组件目录>/render.py 应写到 output，支持任意当前目录。缺失依赖文件必须失败。',
      'context 包保留 parser.parse(payloads,contract)，返回与 transform 一样的封装，调用方使用 <package>.parser 导入。',
      '## 各组件规则']
    from strengthening import NEW_RULES
    if any(s['contract']['operation'] in NEW_RULES for s in specs):
        lines.append('本任务所有输入中的嵌套JSON值也必须合法；NaN/Infinity在未参与计算的字段中同样应抛ValueError。下游必须实际消费所有契约inputs，不能使用固定的上游副本。')
    for spec in specs:
        c=spec['contract']; label,rule=RULES[c['operation']]
        if c['operation'] in ('lag_evidence','integrity_evidence'):
            rule=RULES['failure_evidence'][1]+'\n'+rule
        if c['operation']=='remediation_plan': rule+='\n'+RULES['critical_path'][1]
        lines.extend([f"### {spec['folder']} — {label}",f"输入：`{'`, `'.join(c['inputs'])}`；输出：`{c['output']}`。参数以本组件 contract.json 为准。",rule,f"局部验收：`python3 {spec['folder']}/check_module.py`（先生成依赖及本组件输出）。"])
    lines+=['## 集成与交付',
      '补齐 run_all.py，从任意当前目录启动时定位工作区；执行所有必要组件、已有集成命令与 final_report.py。每个子进程失败必须传播非零退出码；不得吞掉失败、跳过尚未生成的依赖或复用旧 outputs。',
      '已有 integrate.py：`python3 integrate.py` 读取所有组件产物写 outputs/core_manifest.json，内容为 {components:{组件名:result}}。multistage 的 `python3 integrate.py domains` 合并 domains 记录并按(source,id)去重、冲突报错，写 outputs/domain_core.json；仅契约引用此文件时才需要该中间产物。',
      f'补齐 final_report.py，读取 core_manifest，写 outputs/final_report.json：{{title:{title!r},component_count:组件数,sha256:核心对象摘要,attention:需要关注的组件名排序列表}}。摘要对 json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False) 的 UTF-8 字节计算 SHA-256。attention 包含 result.blocked 为真，或 feasible/compatible 显式为假，或 deny>0，或 score_total>=20 的组件；不存在的字段不触发。',
      '## 验收',
      '`python3 check.py` 是可见本地冒烟检查：清理旧 outputs、物化（如适用）、执行 run_all、检查输出结构并运行局部检查。它不包含完整预期结果，也不决定正式得分。正式评分由工作区外的只读 verifier 校验所有受保护文件（包括 check.py 自身）的可信哈希、全部产物与隐藏的边界/变异输入。不要把 _authoring/、verifier/、验证记录或上级目录挂载给被测代理。',
      '## 运行方式']
    if suite=='linux2':
        lines+=['先运行 `python3 materialize.py`；该脚本校验内嵌物化清单的 SHA-256，生成 inputs/、products/ 的契约、检查与缺失实现占位。重复执行会保留实现，只核对受保护生成文件；冲突时失败。随后检查新出现的三个产品目录并实现工具。仅在物化完成后，产品分支才可执行。']
    lines+=['将本 TASK.md 与对应 workspace 单独交给代理。完成实现后，在工作区运行 `python3 check.py`。正式评测命令及信任边界见数据集根 README，代理只需完成此工作区。']
    return '\n\n'.join(lines)+'\n'

def build():
    if DEST.exists(): raise RuntimeError(f'refusing overwrite {DEST}')
    DEST.mkdir(); author=DEST/'_authoring'; author.mkdir(); verifier=DEST/'verifier'; verifier.mkdir()
    for src in ('reference.py','specification.py','build.py','qa.py','strengthening.py'):
        shutil.copy2(HERE/src,author/src)
    for src in ('verify.py','probe.py'):
        shutil.copy2(HERE/src,verifier/src)
    entries=[]; seal={}; specs_all={}
    for index,(suite,name,title,goal,ns,vs,shape) in enumerate(SCENARIOS):
        task=DEST/'tasks'/suite/name; w=task/'workspace'; names=ns.split(); views=vs.split()
        specs,inputs=make_specs(suite,names,views,shape,index)
        prompt=f'完成本地{title} coding任务：{goal}。阅读README及契约，补齐实现和outputs交付物。运行python3 check.py验收；禁止修改输入、契约、README、check.py、check_module.py、integrate.py及materialize.py。'
        assert 140<=len(prompt)<=180,(name,len(prompt))
        write(task/'TASK.md','# Task\n\n'+prompt+'\n')
        write(w/'README.md',readme(suite,name,title,goal,specs)); write(w/'check.py',CHECK); write(w/'integrate.py',INTEGRATE)
        generated={}; editable=[]
        for spec in specs:
            folder=spec['folder']; files=component_files(spec,suite)
            for f,s in files.items():
                if suite=='linux2': generated[f'{folder}/{f}']=s
                else: write(w/folder/f,s)
            editable.extend([f'{folder}/{m}.py' for m in ('model','transform','render')])
        for rel,value in inputs.items():
            s=json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
            if suite=='linux2': generated[rel]=s
            else: write(w/rel,s)
        if suite=='linux2':
            payload=json.dumps(generated,ensure_ascii=False,sort_keys=True,separators=(',',':'))
            payloadhash=hashlib.sha256(payload.encode()).hexdigest()
            materialize=f'''import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PAYLOAD={payload!r}
EXPECTED_SHA256={payloadhash!r}
def main():
    if hashlib.sha256(PAYLOAD.encode('utf-8')).hexdigest()!=EXPECTED_SHA256: raise ValueError('materialization boundary changed')
    files=json.loads(PAYLOAD); protected={{}}
    for rel,s in files.items():
        p=ROOT/rel; editable=p.name in ('model.py','transform.py','render.py')
        if not editable and p.exists() and p.read_bytes()!=s.encode('utf-8'): raise ValueError('generated protected file changed: '+rel)
        p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists(): p.write_text(s,encoding='utf-8',newline='\\n')
        if not editable: protected[rel]=hashlib.sha256(s.encode('utf-8')).hexdigest()
    out=ROOT/'outputs/materialized.json'; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({{'schema':'mixed16.materialized.v2','protected':protected}},sort_keys=True,indent=2)+'\\n',encoding='utf-8')
    print('MATERIALIZED',len(files))
if __name__=='__main__': main()
'''
            write(w/'materialize.py',materialize)
        protected={p.relative_to(w).as_posix():sha(p) for p in sorted(w.rglob('*')) if p.is_file() and p.relative_to(w).as_posix() not in editable}
        generated_protected={rel:hashlib.sha256(s.encode()).hexdigest() for rel,s in generated.items() if rel not in editable}
        key=f'{suite}/{name}'
        seal[key]=dict(initial=protected,generated=generated_protected,task_prompt_sha256=sha(task/'TASK.md'))
        specs_all[key]=dict(title=title,suite=suite,shape=shape,index=index,specs=specs,inputs=inputs,editable=editable)
        files=sorted(p for p in w.rglob('*') if p.is_file()); tree=''.join(p.relative_to(w).as_posix()+'\0'+sha(p)+'\n' for p in files)
        entries.append(dict(entry_id=key,suite=suite,task_name=name,task_name_reused_across_suites=False,task_prompt_sha256=sha(task/'TASK.md'),workspace_tree_sha256=hashlib.sha256(tree.encode()).hexdigest(),workspace_file_count=len(files),entry_file_count=len(files)+1,core_component_count=len(specs),verification_hint='python3 check.py; official external verifier required'))
    dump(author/'task_specs.json',specs_all); dump(verifier/'protected_hashes.json',seal)
    from strengthening import TARGETS
    dump(DEST/'manifest.json',dict(schema_version='semserve.original-tasks.v1',extension_version='3.0.0',strengthened_task_names=sorted(TARGETS),benchmark_entry_count=16,unique_task_name_count=16,suite_counts={s:4 for s in ('multistage4','reasoning4','context8','linux2')},reused_task_names=[],contains_predeclared_dag=False,contains_gold_frontier_or_labels=False,contains_runtime_traces_or_results=False,metadata_scope='tasks/*/*/workspace only; authoring and verifier excluded',explicit_dependency_paths_in_contracts=True,evaluation_goal='Discover executable opportunities from file interfaces; no claim of hidden dependency topology',entries=entries))
    write(DEST/'README.md','''# Mixed16 extension v3

16 个独立任务保留原名，按已有四种目录风格各分4个。v3针对API下线、身份联邦、搜索索引和Linux组4项增加算法与真实结果依赖；其余9项保持v2任务文件逐字节一致。原仓库18个条目未修改。输入规模用于正确性与组合优化，不宣称是更重的性能压力题。

## 四类结构

- multistage4：domains/ + views/，3 个证据领域 + 3 个视图；版本去重、风险排序、负载平衡、条件修复与关键路径。
- reasoning4：engines/，3个算法引擎；API新增带预算/期限的集合覆盖，以及公告释放时间、人员互斥、全局资源容量共同约束的精确调度。
- context8：3个可导入package，保留parser接口；身份联邦新增轮换、祖先撤销传播和循环组继承闭包；搜索新增字段重命名图、分片墓碑恢复和预算仲裁优化。
- linux2：初始仍只有README.md、check.py、integrate.py、materialize.py，物化后3个产品。每项改为两个产品并行、第三个消费二者结果：最宽信任路径与轮换覆盖、备份链与原子事务恢复、法律保留分组背包与日志授权、ECMP与有状态防火墙实际路径核验。linux指原仓库结构风格，标准库验证也支持Windows。

统一 TASK.md、README 章节、契约字段顺序、接口名字与验证流程。核心组件数为3或6，不再统一为8个同构组件。静态夹具含24–55条证据/事件、30个span、40条请求等，并非性能基准；隐藏测试另覆盖空集、非法字段、重复ID/修订冲突、非有限数、分数截断、默认拒绝、偏移缺口及集成冲突。

## 给被测代理的内容

每次仅给 tasks/<suite>/<name>/TASK.md 和对应 workspace/。绝不能挂载本数据集根目录、_authoring/、verifier/ 或旧版备份。契约含输入文件接口，目标是从代码与文件接口发现当前可执行机会，不声称隐藏所有依赖；不提供任务计划DAG、预先标注波次、并行标签或计时策略。算法输入中的业务依赖图是待求解数据，不是评测调度DAG。

## 验收与信任边界

代理在工作区运行 python3 check.py 做本地冒烟验证，没有完整golden。正式评分从可信只读评测器执行：

    python3 verifier/verify.py --entry multistage4/regional_failover_readiness --workspace <candidate-workspace>

外部 verifier 在运行前后校验可信 protected_hashes.json，覆盖 check.py 自身、输入、契约、局部检查和已有集成脚本；linux额外核验物化文件。随后从作者参考算法计算预期、比较全部输出，并用未下发的变更夹具直接调用组件API。缺失实现、篡改检查器、错误输出及只硬编码公开夹具不能获得通过。

这要求 harness 将 verifier/、_authoring/ 置于代理不可读取且不可写入的位置；仅靠在同一可写磁盘保存哈希不是安全沙箱。作者参考实现与测试输入不在workspace内，分发时也应隔离；外部verifier不是恶意Python的进程隔离器。

## 作者工具

_authoring/含任务规格、参考算法和构建/QA脚本；verifier/含独立评分入口、API探针与可信哈希。python3 _authoring/qa.py --root . 重跑参考实现、初始失败、算法捷径及上游结果忽略负例，输出validation_report.json、structure_audit.json、duplicate_audit.json。查重同时比较提示、工作区、完整输入包，以及忽略任务/组件命名后的算法依赖图；共享基础算法或单个夹具不等于任务级重复。正式评测不会填充代理工作区。

本包SHA256SUMS覆盖除其自身及__pycache__之外的分发文件。manifest.workspace_tree_sha256：按相对路径排序，拼接 path+NUL+文件sha256+LF，对UTF-8字节计算SHA-256。原仓库的manifest不合并或篡改；此扩充包独立记录16条目。
''')
    print(DEST,flush=True)

if __name__=='__main__': build()
