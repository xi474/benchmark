"""Validate and package the standalone release, excluding QA solutions and caches."""
import argparse
import ast
import hashlib
import json
import re
import zipfile
from pathlib import Path

def files(root):
    return sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(s,encoding='utf-8',newline='\n')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);root=parser.parse_args().root.resolve()
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    report=json.loads((root/'review/validation_report.json').read_text(encoding='utf-8'))
    seals=json.loads((root/'verifier/protected_hashes.json').read_text(encoding='utf-8'))
    assert manifest['benchmark_entry_count']==report['reference_passed']==report['initial_incomplete_rejected']==6
    assert manifest['core_component_count']==report['core_components']==21
    assert report['status']=='passed'
    missing=0
    for e in manifest['entries']:
        task=root/'tasks'/e['entry_id'];w=task/'workspace'
        assert sha(task/'TASK.md')==e['task_prompt_sha256']
        assert not (w/'outputs').exists() and not (w/'_solution').exists()
        for rel,h in seals[e['entry_id']]['initial'].items():assert sha(w/rel)==h
        tree=''.join(p.relative_to(w).as_posix()+'\0'+sha(p)+'\n' for p in files(w))
        assert hashlib.sha256(tree.encode()).hexdigest()==e['workspace_tree_sha256']
        if e['suite']=='linux2':
            assert {p.name for p in w.iterdir()}=={'README.md','check.py','integrate.py','materialize.py'}
            module=ast.parse((w/'materialize.py').read_text(encoding='utf-8'))
            a={n.targets[0].id:ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('PAYLOAD','EXPECTED','EDITABLE')}
            assert hashlib.sha256(a['PAYLOAD'].encode()).hexdigest()==a['EXPECTED']
            payload=json.loads(a['PAYLOAD'])
            for rel,h in seals[e['entry_id']]['generated'].items():assert hashlib.sha256(payload[rel].encode()).hexdigest()==h
            missing+=sum(rel.endswith('/transform.py') and 'NotImplementedError' in s for rel,s in payload.items())
        else:
            for p in w.rglob('transform.py'):
                assert 'NotImplementedError' in p.read_text();missing+=1
    assert missing==21
    for p in files(root):
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
        if p.suffix=='.json':json.loads(p.read_text(encoding='utf-8'))
    write(root/'review/交付与验收.md',f'''# 六题独立修订集验收

6题、21组件，四类结构均保留。参考解6/6通过，初始未完成实现6/6被拒绝。业务API {report['api_cases']}例，加载器及render接口{report['loader_render_cases']}例，独立手算/枚举6组；另有22个修复定向示例。

硬编码6、缓存上游5、语义变异6、保护文件篡改6均被拒绝；MP11没有组件间文件依赖，因此不计缓存上游负例。初始任务部分得分均0，参考解均满分。具体证据见[验收JSON](validation_report.json)、[定向回归](spec_v2_regression.json)、[部分评分验收](partial_reward_validation.json)。

实跑Python {report['python'].split()[0]} / {report['platform']}。这些结果是作者可解性检查，不是模型baseline。新版模型复测独立保存，旧基线不回填。
''')
    archive=root.parent/(root.name+'-agent.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files(root/'tasks'):z.write(p,p.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and all(x.startswith('tasks/') for x in z.namelist())
        assert sum(x.endswith('/TASK.md') for x in z.namelist())==6
    links=0
    for p in root.rglob('*.md'):
        if 'release_assets' in p.parts:continue # rebuild templates are checked at emitted paths
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if link.startswith(('https:','http:','#')):continue
            assert (p.parent/link.split('#',1)[0]).is_file(),(str(p),link)
            links+=1
    audit=dict(status='passed',entries=6,core_components=21,pristine_missing_implementations=missing,linux_four_file_workspaces=1,local_markdown_links_checked=links,agent_zip_members_only_tasks=True,agent_zip_sha256=sha(archive))
    write(root/'review/package_audit.json',json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    write(root/'SHA256SUMS','\n'.join(sha(p)+'  '+p.relative_to(root).as_posix() for p in files(root) if p.name!='SHA256SUMS')+'\n')
    full=root.parent/(root.name+'-full.zip')
    with zipfile.ZipFile(full,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files(root):z.write(p,root.name+'/'+p.relative_to(root).as_posix())
        z.write(archive,archive.name)
    with zipfile.ZipFile(full) as z:assert z.testzip() is None
    print(json.dumps(audit,ensure_ascii=False))

if __name__=='__main__':main()
