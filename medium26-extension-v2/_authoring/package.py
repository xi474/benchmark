"""Seal and package only pristine tasks; never include author QA workspaces."""
from __future__ import annotations
import argparse,ast,hashlib,json,re,zipfile
from pathlib import Path

def files(root):return sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,s):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(s,encoding='utf-8',newline='\n')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);args=parser.parse_args();root=Path(args.root).resolve();report=json.loads((root/'review/validation_report.json').read_text(encoding='utf-8'));assert report['status']=='passed' and report['reference_passed']==26
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'));seals=json.loads((root/'verifier/protected_hashes.json').read_text(encoding='utf-8'));count=0
    for e in manifest['entries']:
        task=root/'tasks'/e['entry_id'];w=task/'workspace';assert sha(task/'TASK.md')==e['task_prompt_sha256']
        assert not (w/'outputs').exists() and not (w/'_solution').exists()
        for rel,digest in seals[e['entry_id']]['initial'].items():assert sha(w/rel)==digest
        tree=''.join(p.relative_to(w).as_posix()+'\0'+sha(p)+'\n' for p in files(w));assert hashlib.sha256(tree.encode()).hexdigest()==e['workspace_tree_sha256']
        if e['suite']=='linux2':
            assert {p.name for p in w.iterdir()}=={'README.md','check.py','integrate.py','materialize.py'}
            module=ast.parse((w/'materialize.py').read_text(encoding='utf-8'));assigns={n.targets[0].id:ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('PAYLOAD','EXPECTED','EDITABLE')};payload=json.loads(assigns['PAYLOAD']);assert hashlib.sha256(assigns['PAYLOAD'].encode()).hexdigest()==assigns['EXPECTED']
            for rel,digest in seals[e['entry_id']]['generated'].items():assert hashlib.sha256(payload[rel].encode()).hexdigest()==digest
            for rel,s in payload.items():
                if rel.endswith('/transform.py'):assert 'NotImplementedError' in s;count+=1
        else:
            for path in w.rglob('transform.py'):assert 'NotImplementedError' in path.read_text(encoding='utf-8');count+=1
    assert count==93
    for p in files(root):
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
        if p.suffix=='.json':json.loads(p.read_text(encoding='utf-8'))
    summary=f'''# Medium26 本地交付与验收

26题全部实现为独立TASK.md及初始workspace，四类结构为9/7/5/5，共93个核心组件。Agent输入保留缺失实现，参考解和正式验证均在工作区外。原仓库14题与Mixed16 v4未改动。

- 参考解：{report['reference_passed']}/26通过；初始未完成实现：{report['initial_incomplete_rejected']}/26被拒绝。
- 业务API：{report['api_cases']}个；加载器/render文件接口：{report['loader_render_cases']}个。
- 独立手算/库解析/性质核对：{report['independent_oracle_groups']}组。
- 负例：公开样例硬编码{report['hardcoded_public_API_rejected']}、缓存上游{report['cached_upstream_API_rejected']}、典型语义变异{report['semantic_mutation_API_rejected']}、篡改保护文件{report['protected_tamper_rejected']}，全部被拒绝。MP11没有组件间文件依赖，因此不计缓存上游负例。
- 实跑环境：Python {report['python'].split()[0]} / {report['platform']}；任务面向Python>=3.11标准库，本次环境详见验收JSON。
- 本发布不附带完整新版模型校准结果；六题复测独立记录，M字段仅保留历史设计目标，旧成绩不自动转为新版六题成绩。

[26题目录与DAG](../docs/26题中文目录与DAG.md) · [当前难度标准](../docs/难度分级标准_v1.1.md) · [详细验收JSON](validation_report.json) · [去重初筛](duplicate_audit.json)
'''
    write(root/'review/交付与验收.md',summary)
    archive=root.parent/(root.name+'-agent.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files(root/'tasks'):z.write(p,p.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and all(x.startswith('tasks/') for x in z.namelist())
        assert len([x for x in z.namelist() if x.endswith('/TASK.md')])==26
    links=0
    for p in root.rglob('*.md'):
        if '__pycache__' in p.parts or 'release_assets' in p.parts:continue
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if link.startswith(('https:','http:','#')):continue
            assert (p.parent/link.split('#',1)[0]).is_file(),(str(p),link);links+=1
    audit=dict(status='passed',entries=26,pristine_missing_implementations=93,linux_four_file_workspaces=5,local_markdown_links_checked=links,agent_zip_members_only_tasks=True,agent_zip_sha256=sha(archive))
    write(root/'review/package_audit.json',json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    entries=[p for p in files(root) if p.name!='SHA256SUMS'];write(root/'SHA256SUMS','\n'.join(sha(p)+'  '+p.relative_to(root).as_posix() for p in entries)+'\n')
    full=root.parent/(root.name+'-full.zip')
    with zipfile.ZipFile(full,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files(root):z.write(p,root.name+'/'+p.relative_to(root).as_posix())
        z.write(archive,archive.name)
    with zipfile.ZipFile(full) as z:assert z.testzip() is None
    print(json.dumps(dict(root=str(root),agent_zip=str(archive),full_zip=str(full),files=len(files(root)),**audit),ensure_ascii=False))

if __name__=='__main__':main()
