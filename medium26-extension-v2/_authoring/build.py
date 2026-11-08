from __future__ import annotations
import argparse,collections,hashlib,json,re,shutil,sys
from pathlib import Path
from reference import TASKS,RULES
from templates import CHECK,CHECK_MODULE,INTEGRATE
from draw_dags import graph,render
HERE=Path(__file__).resolve().parent
SOURCE_REVISIONS={
 'swe_verified_data':'78f471bf655a3137b2e8a75af1501690ec009ec3',
 'swe_pro_data':'2d52cb3df914a3fcf80c7f66738b3a88ae37fc50',
 'swe_pro_repository':'66f92766bba642462d4bbe5479e83f91f9211862',
 'terminal_bench_repository':'2fd12b88aafdd04a52c298e3940bcb189f9766d6',
 'gaia2_data':'78ea3bdbdeec2bdcd6afa5420915d8a22f23ed99',
 'gaia2_are_repository':'a9fd2edccb4bc7e22fbf45c8482a5fef30a2a5a4'}

def write(path,text):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8',newline='\n')
def dump(path,value):write(path,json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def tree_hash(root):
    files=sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return hashlib.sha256(''.join(p.relative_to(root).as_posix()+'\0'+digest(p)+'\n' for p in files).encode()).hexdigest()

STYLE_NOTES={
'multistage4':'domains/负责不同领域/表示，views/消费领域产物，保留真实的分叉与汇合；组件数由业务决定。',
'reasoning4':'engines/分别实现算法内核，输入/输出文件接口表达算法之间真实依赖。',
'context8':'独立可导入package保留parser.parse(payloads,contract)稳定接口，修复包内实现及跨包兼容。',
'linux2':'初始仅README.md、check.py、integrate.py、materialize.py四个文件；物化后出现inputs/及products/，保留产品实现。linux指原仓库组织风格，不要求root或Linux系统。'}

def readme(t):
    meta=t['source_metadata'];title=t['title'];lines=[f'# {title}：接口与完整规格','',meta['goal'],'',
      '## 环境与实现范围','',
      'Python 3.11及以上，仅标准库；本地合成输入，无GPU、训练、网络、真实账号或实时等待。所有时间按本题显式规则处理，禁止读取当前日期替代输入日期。',
      STYLE_NOTES[t['style']],
      '组件实现model.py、transform.py、render.py，以及根run_all.py和final_report.py；可新增私有辅助模块。未提供的实现文件需要自行创建。',
      'README.md、TASK.md、inputs/、contract.json、check_module.py、check.py、integrate.py以及适用的materialize.py、__init__.py、parser.py不可修改。初始输入和契约为任务规格，不是可以修正的错误数据。','',
      '## 稳定接口与通用边界','',
      '- model.load_payload(path:Path)：读取UTF8 JSON，仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。',
      '- transform.transform(payloads:list,contract:dict)：payloads按contract.inputs顺序，数量必须一致。返回恰好{"name":contract["name"],"result":算法结果对象}；本说明中的输出均指result，不额外套一层封装。',
      '- 当输入对象键恰为name/result时，仅其result为业务输入；其他对象原样解释。不修改payloads/contract（包括嵌套值），不硬编码公开输入或上游结果。',
      '- render.build_component(root:Path,contract_path:Path)：从给定root读取所有输入，调用transform并返回封装。执行python3 <组件目录>/render.py时，将封装写入contract.output；必须支持任意当前目录。缺文件或子命令失败须失败。',
      '- context包另外保留<package>.parser.parse(payloads,contract)，返回与transform完全一致的封装。不要修改稳定parser来绕过实现。',
      '- 必需字段缺失、指定非法类型/重复/冲突均ValueError。整数排除bool，有限数允许int/float但排除bool及非有限数，布尔字段必须bool；无明示默认值不自行补默认。未知额外字段可忽略，但其中非有限JSON仍非法。所有合法空集/无解按照各operation输出。',
      '- 字符串排序按Python通常字典序；非空字符串要求strip后非空，但除规则明示外保留原内容。安全相对路径使用/，禁止绝对路径、反斜线、冒号、空段、.和..。hex按bytes.fromhex解释，不将hex文本当字节计算摘要。',
      '- 数值计算比较容差为相对/绝对1e-9；非数值结构、键集合、列表顺序、文本/字节格式必须精确。输入中的算法图是业务数据，不是Agent执行计划。','',
      '## 各组件业务规则','']
    for folder,c in t['components']:
        lines.extend([f'### {folder}','',f'operation：`{c["operation"]}`。输入文件及顺序见`{folder}/contract.json`，输出为`{c["output"]}`。',RULES[c['operation']],'',f'局部检查：`python3 {folder}/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。',''])
    lines.extend(['## 集成、JSON与最终报告','',
      '所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。',
      '实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。',
      f'实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为{title!r}，component_count为components键数。',
      'sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。',
      'attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。','',
      '## 运行与验收',''])
    if t['style']=='linux2':lines.extend(['先运行python3 materialize.py。受保护脚本验证内嵌清单哈希，生成输入、产品契约、检查及实现占位；重复执行保留已有实现，并验证生成的受保护文件。不得修改物化器或其生成的输入/契约/检查。此处文件操作基于本地快照，禁止操作真实home或账号。',''])
    lines.extend(['在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。',
      'Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。',''])
    return re.sub(r'\n{3,}','\n\n','\n\n'.join(lines))

def component_files(folder,c,suite):
    depth=len(Path(folder).parts);package_check=(f"assert importlib.import_module({(folder+'.parser')!r}).parse(copy.deepcopy(before),copy.deepcopy(cc))==result" if suite=='context8' else 'pass')
    files={'contract.json':json.dumps(c,ensure_ascii=False,indent=2)+'\n','check_module.py':CHECK_MODULE.replace('DEPTH',str(depth)).replace('PACKAGE_CHECK',package_check)}
    files['model.py']='def load_payload(path):\n    raise NotImplementedError("implement JSON model loader")\n'
    files['transform.py']='def transform(payloads,contract):\n    raise NotImplementedError("implement the business contract")\n'
    files['render.py']='def build_component(root,contract_path):\n    raise NotImplementedError("implement file interface")\n\nif __name__=="__main__":\n    raise NotImplementedError("implement component CLI")\n'
    if suite=='context8':files.update({'__init__.py':'','parser.py':'from .transform import transform\n\ndef parse(payloads,contract):\n    return transform(payloads,contract)\n'})
    return files

def materializer(generated,editable):
    payload=json.dumps(generated,ensure_ascii=False,sort_keys=True,separators=(',',':'));expected=hashlib.sha256(payload.encode()).hexdigest()
    return f'''import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PAYLOAD={payload!r}
EXPECTED={expected!r}
EDITABLE={editable!r}
def main():
    if hashlib.sha256(PAYLOAD.encode()).hexdigest()!=EXPECTED:raise ValueError('materialization manifest changed')
    for rel,content in json.loads(PAYLOAD).items():
        path=ROOT/rel
        if ROOT not in path.resolve().parents or path.is_symlink():raise ValueError('unsafe materialized path')
        if path.exists() and rel not in EDITABLE and path.read_bytes()!=content.encode():raise ValueError('generated protected file changed: '+rel)
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():path.write_text(content,encoding='utf-8',newline='\\n')
    print('MATERIALIZED')
if __name__=='__main__':main()
'''

def build(dest):
    dest=Path(dest).resolve()
    if dest.exists():raise ValueError('refusing to overwrite existing package: '+str(dest))
    dest.mkdir(parents=True);author=dest/'_authoring';verifier=dest/'verifier';review=dest/'review';author.mkdir();verifier.mkdir();review.mkdir()
    for src in HERE.glob('*.py'):
        if src.name not in ('verify.py','probe.py'):shutil.copy2(src,author/src.name)
    for name in ['candidate_metadata.json','difficulty_standard.md']:shutil.copy2(HERE/name,author/name)
    for name in ['verify.py','probe.py']:shutil.copy2(HERE/name if (HERE/name).is_file() else HERE.parent/'verifier'/name,verifier/name)
    entries=[];seals={};graphs=[];catalog=['# Medium26 v2：26题中文目录','',
      '26题全部纳入实现版；这里的难度与并行优势仍是待实验校准的设计标签。每题说明链接指向正式TASK及README，作者DAG由实际contract.inputs生成。','',
      '[当前难度分级标准](难度分级标准_v1.1.md) · [验收结果](../review/validation_report.json) · [来源与范围](../NOTICE.md)','']
    for t in TASKS:
        suite=t['style'];key=suite+'/'+t['slug'];task=dest/'tasks'/suite/t['slug'];w=task/'workspace';editable=['run_all.py','final_report.py'];generated={}
        goal=t['source_metadata']['goal'].rstrip('。')
        prompt=f'# {t["title"]}\n\n{goal}。阅读工作区README.md和各组件contract.json，补齐缺失Python实现并从输入重新计算全部组件结果与最终报告。仅使用标准库，保持稳定接口，不得硬编码样例输出。\n\n实现各组件model.py、transform.py、render.py以及run_all.py、final_report.py；根据实际文件接口确定执行条件。完成后运行python3 check.py。不得修改任务说明、README、输入、契约、检查器、integrate.py、稳定parser及适用的materialize.py。公开检查仅为冒烟，正式评分在工作区外进行。\n'
        write(task/'TASK.md',prompt);write(w/'README.md',readme(t));write(w/'check.py',CHECK);write(w/'integrate.py',INTEGRATE)
        for folder,c in t['components']:
            fs=component_files(folder,c,suite)
            for module in ['model.py','transform.py','render.py']:editable.append(folder+'/'+module)
            for name,content in fs.items():
                if suite=='linux2':generated[folder+'/'+name]=content
                else:write(w/folder/name,content)
        case=json.dumps(t['fixture'](47),ensure_ascii=False,sort_keys=True,indent=2)+'\n'
        if suite=='linux2':generated['inputs/case.json']=case;write(w/'materialize.py',materializer(generated,editable))
        else:
            write(w/'inputs/case.json',case)
            write(w/'run_all.py','raise NotImplementedError("implement orchestration from file contracts")\n')
            write(w/'final_report.py','raise NotImplementedError("implement report")\n')
        initial={p.relative_to(w).as_posix():digest(p) for p in w.rglob('*') if p.is_file() and p.relative_to(w).as_posix() not in editable};gen={rel:hashlib.sha256(content.encode()).hexdigest() for rel,content in generated.items() if rel not in editable};seals[key]=dict(initial=initial,generated=gen)
        entries.append(dict(entry_id=key,task_id=t['id'],suite=suite,task_name=t['slug'],title=t['title'],difficulty='M',difficulty_calibrated=False,source_group=t['source_metadata']['source_group'],source_instances=[x['id'] for x in t['source_metadata']['sources']],task_prompt_sha256=digest(task/'TASK.md'),workspace_tree_sha256=tree_hash(w),initial_workspace_file_count=sum(p.is_file() for p in w.rglob('*')),core_component_count=len(t['components']),verification_entry_id=key))
        g=graph(t);graphs.append(g);dag=author/'dags'/t['id'];dag.parent.mkdir(parents=True,exist_ok=True);render(g,dag)
        catalog.extend([f'## {t["id"]} · {t["title"]}','',f'风格：`{suite}`；实现单元：{len(t["components"])}；[TASK](../tasks/{key}/TASK.md) · [完整接口规格](../tasks/{key}/workspace/README.md)。',t['source_metadata']['medium_basis'],'',f'![{t["id"]} DAG](../_authoring/dags/{t["id"]}.png)',''])
    dump(verifier/'protected_hashes.json',seals);dump(author/'task_graphs.json',graphs)
    dump(dest/'manifest.json',dict(schema_version='semserve.medium26.v2',extension_version='2.0.0',previous_version='1.0.0',difficulty_metadata_role='historical_design_target',changed_task_ids=['MP04', 'MP08', 'MP09', 'MP10', 'MP11', 'MP24'],benchmark_entry_count=26,unique_task_name_count=26,suite_counts=dict(collections.Counter(t['style'] for t in TASKS)),core_component_count=sum(len(t['components']) for t in TASKS),contains_predeclared_dag=False,contains_gold_frontier_or_labels=False,metadata_scope='TASK.md and initial workspace only; _authoring/verifier/docs/review excluded from agent mounts',explicit_dependency_paths_in_contracts=True,difficulty_standard='v1.1',difficulty_calibration='not_run_for_v2',source_benchmark_equivalence=False,entries=entries))
    write(dest/'docs/26题中文目录与DAG.md','\n'.join(catalog))
    standard=(HERE/'difficulty_standard.md').read_text(encoding='utf-8').replace('当前难度分级标准 v1.0','当前难度分级标准 v1.1').replace('当前候选只有设计预估，尚无参考解验收、模型通过率或并行提速证据','本批已加入参考解与功能验收；难度仍为设计预估，尚无模型通过率或并行提速证据').replace('当前候选尚未完成这些检查','本发布作者验收见review/validation_report.json').replace('本规范与 26 题候选一并归档','本规范与 26 题实现版一并归档')
    write(dest/'docs/难度分级标准_v1.1.md',standard)
    notes=['# 来源与改造说明','',
      '此包为26个公开候选方向的本地独立重实现，夹具为新合成数据，未分发官方gold patch、账号、原始GAIA2 parquet或完整上游工程。正式任务不等价于SWE/Pro/Terminal/GAIA2原任务，分数不能直接比较。来源数据版本沿用2026-11-03/04的候选审查快照。','',
      'GAIA2来源数据标注CC BY 4.0；本包保留来源ID和链接，并明确静态计划化及语义删减。其余来源保留公开实例归属；未将整个上游项目许可改写为本包许可。','',
      '## 明确的范围修订','',
      '- MP02只拼一个变化轴，拒绝重叠坐标；MP03只做fstab/AIX/Linux mount三种固定离线语法。',
      '- MP04采用JSON/CSV/JSONL，JSONL代替原Parquet；普通空值规则写入TASK规格。',
      '- MP06/07/08/09/10/11/12/26输出本地状态/通知/采购计划，不发真实消息或付款；没有多轮反馈。',
      '- MP15限制模块/直属函数和赋值类型注释；MP16限制签名、文档指令和给定MRO。',
      '- MP17公开确定性multipart字节协议；MP18使用四种自包含MANIFEST指令；MP19不执行源码。',
      '- MP20保留schema与引用验证的阶段边界，引用错误原子回退；MP21JSON/内存SQLite替代服务。',
      '- MP22只接受有限MARC XML和给定语言代码；MP23索引也分块，空行/无末尾换行/空文件逐字节恢复。',
      '- MP24修订来源参考查询的跨部门计数：必须某一部门人数>10，EU资格部门可以不同。两个部门各6人不入选。',
      '- MP25直接提供文本，移除OCR；MP26“下周五”明确为下一自然周周五，两端含今天/末日。','']
    for t in TASKS:
        notes.extend([f'## {t["id"]} {t["title"]}','',*['- ['+x['id']+']('+x['url']+')' for x in t['source_metadata']['sources']],''])
    write(dest/'NOTICE.md','\n'.join(notes));dump(review/'source_revisions.json',SOURCE_REVISIONS)
    write(dest/'README.md','''# Medium26 extension v1

26个中等设计目标任务，93个核心组件，均为Python标准库、本地小型合成数据。任务由公开基准候选改造成本仓库已有的TASK.md + workspace格式。原14题与Mixed16 v4保持原有版本；本扩充包有独立manifest与seal。

## 四类结构

- multistage4：9题，domains/views承载领域解析与下游结果汇合。
- reasoning4：7题，engines承载标准算法、静态分析和有界状态规划。
- context8：5题，可导入package和受保护parser接口，修复跨接口兼容。
- linux2：5题，初始四文件，materialize后生成products及输入；不要求真实Linux、root或网络。

组件数按业务为3–5，未统一堆成同构节点，也没有按历史suite名字强制4/8个Agent。DAG由实际contract.inputs生成，位于_authoring/dags，仅供作者审查。任务难度与实际并行收益仍需模型实验校准。

## 入口

- [26题中文目录及DAG](docs/26题中文目录与DAG.md)
- [当前难度分级标准v1.1](docs/难度分级标准_v1.1.md)
- [来源与明确改造范围](NOTICE.md)
- [作者验收结果](review/validation_report.json)
- [去重与结构审查](review/duplicate_audit.json)
- [26题Agent任务包](../medium26-extension-v1-agent.zip)

## 给Agent的材料

每次仅提供tasks/<suite>/<task>/TASK.md和对应初始workspace。不要将本扩充包整体、_authoring、verifier、review、DAG、参考解或其他任务挂载进Agent执行环境。合同中的输入文件接口是公开实现规范，Agent据此自行发现依赖。

Agent在工作区运行python3 check.py做本地冒烟。正式评分在可信评测环境运行：

```bash
python3 verifier/verify.py --entry reasoning4/grouped_feature_union --workspace /path/to/candidate/workspace
```

entry见manifest.json。正式验证包含受保护文件前后哈希、全部输出、不同输入的业务API、JSON加载器与render文件接口，不能用本地check替代。验证器需要与Agent可读写区域隔离；它不是恶意Python的系统沙箱。

## 复验与重建

Python>=3.11；验证器/参考算法/任务本身仅标准库。作者重新绘制PNG需要Pillow及中文字体，分发的PNG/SVG已预生成。

```bash
python3 _authoring/qa.py --root . --work /tmp/medium26-author-qa
python3 _authoring/build.py --dest /tmp/new-medium26
```

QA工作目录只放作者测试工作区，禁止当Agent输入。实验模型通过率/串并行提速未运行；作者参考解通过不是模型解题成绩。

manifest记录TASK与初始工作区哈希；workspace_tree_sha256按相对路径排序拼接path+NUL+文件sha256+LF再求SHA256。SHA256SUMS不包含自身、压缩包或Python缓存。Agent zip只含TASK及初始workspace，不含答案/隐藏向量。
''')
    extras=HERE/'release_assets'
    if extras.is_dir():
        shutil.copytree(extras,dest,dirs_exist_ok=True)
        shutil.copytree(extras,author/'release_assets')
    print(json.dumps(dict(root=str(dest),entries=len(entries),components=sum(x['core_component_count'] for x in entries)),ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--dest',required=True);args=parser.parse_args();build(args.dest)
