"""Export contract-level execution graphs with separately stored prediction targets."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent/'medium30-core-v1'
DEST=ROOT

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def lines(name,rows):
    (DEST/name).write_text(''.join(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n' for r in rows),encoding='utf-8')
def pointer(value,path):
    for key in path.strip('/').split('/') if path.strip('/') else []:value=value[int(key)] if isinstance(value,list) else value[key]
    return value

def main():
    DEST.mkdir(exist_ok=True);manifest=read(PACKAGE/'manifest.json');catalog=read(PACKAGE/'verifier/catalog.json')
    tasks=[];components=[];graphs=[];edges=[];pairs=[];ready_states=[];features=[];bindings_checked=0;API_payloads_checked=0
    for task in manifest['tasks']:
        ident=task['id'];work=PACKAGE/task['entry']/'workspace';flow=read(work/'workflow.json');contracts={c['name']:read(work/c['folder']/'contract.json') for c in flow['components']}
        ids={name:ident+'::'+name for name in contracts};producers={};writes={};reads={};deps={name:set() for name in contracts}
        for name,c in contracts.items():
            writes[name]={c['output'],*c.get('emit',{})}
            for path in writes[name]:assert path not in producers,(ident,path);producers[path]=name
        for name,c in contracts.items():
            reads[name]={binding.partition('#')[0] for binding in c['bindings'].values()}
            for key,binding in c['bindings'].items():
                path,_,fragment=binding.partition('#');parent=producers.get(path)
                if parent:
                    deps[name].add(parent);edges.append(dict(task_id=ident,producer_id=ids[parent],consumer_id=ids[name],artifact=path,consumer_payload_key=key,json_pointer=fragment,label_source='declared_file_contract'))
                else:assert (work/path).is_file(),(ident,name,path)
                bindings_checked+=1
        completed=set()
        while len(completed)<len(contracts):
            batch={n for n in contracts if n not in completed and deps[n]<=completed};assert batch,(ident,'cycle');completed|=batch
        def ancestors(n):return deps[n]|set().union(*(ancestors(x) for x in deps[n])) if deps[n] else set()
        reach={n:ancestors(n) for n in contracts}
        prompt=(PACKAGE/task['entry']/'TASK.md').read_text(encoding='utf-8')
        tasks.append(dict(dataset_id='medium30-core-v1',task_id=ident,title=task['title'],style=task['style'],task_path=task['entry']+'/TASK.md',workspace_path=task['entry']+'/workspace',workflow_path=task['entry']+'/workspace/workflow.json',design_difficulty='M',empirical_difficulty=None,component_ids=sorted(ids.values()),source_ids=task['source_ids']))
        for comp in flow['components']:
            name=comp['name'];c=contracts[name];spec=(work/comp['folder']/'SPEC.md').read_text(encoding='utf-8')
            components.append(dict(task_id=ident,component_id=ids[name],name=name,folder=comp['folder'],spec_text=spec,contract=c,reads=sorted(reads[name]),writes=sorted(writes[name]),dependencies=sorted(ids[n] for n in deps[name])))
        graphs.append(dict(dataset_id='medium30-core-v1',task_id=ident,nodes=sorted(ids.values()),edges=[[ids[p],ids[n]] for n in sorted(deps) for p in sorted(deps[n])],label_scope='module_execution_file_dependencies',not_agent_coding_schedule=True))
        for a,b in itertools.combinations(sorted(contracts),2):
            write_conflict=bool(writes[a]&writes[b]);a_before_b=a in reach[b];b_before_a=b in reach[a]
            can_parallel=not a_before_b and not b_before_a and not write_conflict and not (writes[a]&reads[b]) and not (writes[b]&reads[a])
            pair_id=ident+'::'+a+'||'+b
            pairs.append(dict(pair_id=pair_id,task_id=ident,a=ids[a],b=ids[b],relation='a_before_b' if a_before_b else 'b_before_a' if b_before_a else 'unordered_by_dependency',parallel_permitted_by_file_contract=can_parallel,shared_reads=sorted(reads[a]&reads[b]),write_conflict=write_conflict,label_scope='execution_contract_not_coding_order'))
            features.append(dict(pair_id=pair_id,task_id=ident,task_text=prompt,component_a_name=a,component_a_spec=contracts[a]['spec'],component_b_name=b,component_b_spec=contracts[b]['spec']))
        for size in range(len(contracts)+1):
            for subset in itertools.combinations(sorted(contracts),size):
                done=set(subset)
                if any(not deps[n]<=done for n in done):continue
                ready=sorted(n for n in contracts if n not in done and deps[n]<=done)
                ready_states.append(dict(state_id=ident+'::'+','.join(subset),task_id=ident,completed_component_ids=sorted(ids[n] for n in done),ready_component_ids=[ids[n] for n in ready],is_terminal=len(done)==len(contracts),assumption='completed_nodes_succeeded',label_source='enumerated_dependency_ideals_not_agent_trajectory'))
        vectors=read(PACKAGE/catalog['tasks'][ident]['vectors'])
        for i,case in enumerate(vectors['integration']):
            blobs={'inputs/request.json':case['input']}
            for comp in flow['components']:
                name=comp['name'];c=contracts[name]
                payload={k:pointer(blobs[b.partition('#')[0]],b.partition('#')[2]) for k,b in c['bindings'].items()}
                assert payload==vectors['components'][name][i]['payload'],(ident,name,i,'binding mismatch')
                blobs[c['output']]=case['results'][name];API_payloads_checked+=1
    for name,data in [('tasks.jsonl',tasks),('components.jsonl',components),('graphs.jsonl',graphs),('dependency_edges.jsonl',edges),('pair_labels.jsonl',pairs),('ready_states.jsonl',ready_states),('text_features.jsonl',features)]:lines(name,data)
    # Check actual serialized join keys, rather than only the pre-serialization lists.
    parse=lambda f:[json.loads(x) for x in (DEST/f).read_text(encoding='utf-8').splitlines()]
    actual_pairs=parse('pair_labels.jsonl');actual_features=parse('text_features.jsonl');assert {x['pair_id'] for x in actual_pairs}=={x['pair_id'] for x in actual_features}
    report=dict(status='passed',tasks=len(tasks),components=len(components),dependency_edges=len(edges),component_pairs=len(pairs),parallel_contract_pairs=sum(x['parallel_permitted_by_file_contract'] for x in pairs),ready_states=len(ready_states),input_bindings_checked=bindings_checked,integration_to_API_payloads_checked=API_payloads_checked,serialized_pair_feature_joins_checked=len(pairs),scope='static_contract_labels_no_speedup_or_agent_action_claims')
    write(DEST/'validation.json',report)
    (DEST/'README.md').write_text('''# 并行预测器数据入口 v1

本导出对应[medium30-core-v1](../medium30-core-v1/README.md)全部30题、94个业务组件。原题面、输入、SPEC、contract、workflow、参考解和正式verifier均在该完整数据集目录；本目录给出机器可读索引和静态执行标签，不删减原题信息。

## 文件

- tasks.jsonl：任务、组件ID与完整题目文件路径。
- components.jsonl：完整组件规格、contract、读写文件和直接依赖。
- graphs.jsonl / dependency_edges.jsonl：组件文件依赖DAG和每条边的输入绑定证据。
- pair_labels.jsonl：每对组件的先后关系与文件契约是否允许并行。A/B按组件名排序，不按拓扑序排列，避免标签被位置直接暴露。
- ready_states.jsonl：对DAG所有合法已完成集合推导的执行就绪集。
- text_features.jsonl：只保留任务文本与两个组件的业务规格，按pair_id连接标签；排除了显式bindings/output/depends字段。
- validation.json：JSONL联结、路径、DAG和正式验收向量的数据绑定检查。
- parallel-pipeline-validation.json：用两进程按导出的DAG运行30题参考实现，逐题检查组件结果、额外产物和受保护文件；全部通过。这是参考解组件执行检查，不是Agent实测或加速比。

## 获取全部信息

- [完整任务、规格、输入、来源、参考解和verifier](../medium30-core-v1/README.md)
- [全部30题的实际DAG图](../medium30-core-v1/docs/30题目录与实际DAG.md)
- [完整题包ZIP](../medium30-core-v1-full.zip)、[Agent初始包ZIP](../medium30-core-v1-agent.zip)、[Harbor执行包ZIP](../medium30-core-v1-harbor.zip)、[本预测器补充包ZIP](../medium30-parallel-prediction-v1.zip)

将本目录与medium30-core-v1放在同一父目录。重新导出：`python export_prediction.py --package ../medium30-core-v1 --output .`。参考解并行检查：`python validate_parallel_pipeline.py --package ../medium30-core-v1 --export . --output parallel-pipeline-validation.json`，使用与任务一致的Linux Python3.12/Git/NumPy/SciPy环境。

## 训练口径

标签描述“模块产物执行依赖”：A_before_B表示执行B需要A的产物。它不表示写B的代码必须等A完成；编码并行策略需要独立标注。parallel_permitted_by_file_contract只表示声明的文件契约允许并行，不是所有可能实现的线程安全保证，也不是实测加速比。

graphs、components中的dependencies、workflow、contract.bindings直接含有标签真值。若预测目标就是这些依赖，不应把这些字段直接用作模型输入；完整信息保留用于出题、核验和其他预测任务。text_features只是一个可选文本输入视图，最终输入定义由训练方确定。

ready_states由同一DAG推导，并非新的独立实测样本或Agent动作轨迹。训练/验证/测试至少按task_id分组，建议进一步按来源/算法家族分组，避免同题组件对随机拆分造成泄漏。30题、102个组件对适合先验证数据管道；不能据此声称大规模泛化能力。

所有路径相对medium30-core-v1数据集根；读取JSONL请使用UTF-8。标签版本为parallel-contract-export-v1。任务和评分规则未因导出而改变。
''',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,default=PACKAGE);p.add_argument('--output',type=Path,default=DEST);a=p.parse_args();PACKAGE=a.package.resolve();DEST=a.output.resolve();main()
