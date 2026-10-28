"""Render author-only component DAGs; requires networkx and Pillow.

python render_dags.py --root mixed16-extension-v3 --output <gallery>
No task workspace or benchmark contract is modified.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import html
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import networkx as nx
from PIL import Image, ImageDraw, ImageFont

LABELS={
 'lag_evidence':'延迟证据与修订去重','failure_evidence':'失败率证据与修订去重','integrity_evidence':'完整性证据与修订去重',
 'risk_ranking':'阈值筛选与风险排序','review_balance':'审核负载分配','remediation_plan':'修复波次与关键路径',
 'weighted_intervals':'加权区间选择','capacity_assignment':'技能与容量约束分配','critical_path':'依赖波次与关键路径',
 'notice_coverage':'预算与期限下的公告覆盖','resource_cutover':'精确资源受限下线调度','settlement_decode':'新旧清算事件兼容',
 'event_windows':'修订去重与窗口统计','trace_correlation':'扁平 / 嵌套链路关联','schema_compatibility':'声明模式兼容判定',
 'session_replay':'令牌轮换与撤销传播','federation_authorize':'组继承闭包与联合授权','event_decode':'新旧事件编码兼容',
 'checkpoint_replay':'连续确认偏移恢复','schema_migration':'重命名图与模式迁移','shard_replay':'分片缺口与墓碑恢复',
 'quorum_cutover':'预算与副本仲裁优化','trust_paths':'最宽有效信任路径','policy_precedence':'通配策略优先级判定',
 'certificate_schedule':'信任与策略约束的轮换覆盖','recovery_chain':'恢复点与备份链成本优化','transaction_replay':'连续 LSN 与原子事务重放',
 'restore_join':'快照与日志恢复一致性核验','log_compatibility':'混合格式日志脱敏','retention_optimizer':'法律保留与分类配额背包',
 'retention_audit':'保留计划与审计覆盖授权','ecmp_routes':'故障后的等价最短路径集','stateful_acl':'时序连接状态防火墙',
 'network_join':'路由与状态决策联合核验',
}
COLORS={
 'component':('#eff6ff','#2563eb'), 'materialize':('#fff7ed','#c2410c'),
 'integration':('#f5f3ff','#7c3aed'), 'report':('#ecfdf5','#047857'),
}

def dump(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def write(path,value): path.write_text(value.rstrip('\n')+'\n',encoding='utf-8',newline='\n')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def actual_contracts(root,key,spec):
    w=root/'tasks'/key/'workspace'; generated={}
    if spec['suite']=='linux2':
        # Inspect the real materializer without executing it or polluting a workspace.
        tree=ast.parse((w/'materialize.py').read_text(encoding='utf-8'))
        constants={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('PAYLOAD','EXPECTED_SHA256')}
        assert hashlib.sha256(constants['PAYLOAD'].encode()).hexdigest()==constants['EXPECTED_SHA256']
        generated=json.loads(constants['PAYLOAD'])
    observed=[]
    for s in spec['specs']:
        rel=s['folder']+'/contract.json'
        raw=generated[rel] if generated else (w/rel).read_text(encoding='utf-8')
        c=json.loads(raw); assert c==s['contract'],key+': contract/spec mismatch'
        for p in c['inputs']:
            if p.startswith('inputs/'):
                raw_input=generated[p] if generated else (w/p).read_text(encoding='utf-8')
                assert json.loads(raw_input)==spec['inputs'][p]
        observed.append((s['folder'],c,hashlib.sha256(raw.encode('utf-8')).hexdigest()))
    return observed

def graph_for(root,key,spec,audit):
    observed=actual_contracts(root,key,spec); g=nx.DiGraph(); local={}; owners={}; sources={}
    for folder,c,digest in observed:
        ident='component:'+c['name']; owners[c['output']]=ident
        g.add_node(ident,name=c['name'],kind='component',role=folder.split('/')[0] if '/' in folder else 'package',
          label=LABELS[c['operation']],operation=c['operation'],folder=folder,output=c['output'],contract=folder+'/contract.json',contract_sha256=digest)
        local[ident]=[p for p in c['inputs'] if p.startswith('inputs/')]
        for path in local[ident]: sources.setdefault(path,[]).append(ident)
    if any('outputs/domain_core.json' in c['inputs'] for folder,c,_ in observed):
        owners['outputs/domain_core.json']='integration:domains'
        g.add_node('integration:domains',name='integrate.py domains',kind='integration',label='合并全部 domains 证据',output='outputs/domain_core.json')
        for folder,c,_ in observed:
            if folder.startswith('domains/'): g.add_edge('component:'+c['name'],'integration:domains',reason='domain evidence read',path=c['output'])
    for folder,c,_ in observed:
        for path in c['inputs']:
            if path in owners: g.add_edge(owners[path],'component:'+c['name'],reason='contract input',path=path)
            else: assert path in spec['inputs'],(key,path)
    if spec['suite']=='linux2':
        g.add_node('materialize',name='materialize.py',kind='materialize',label='校验边界并生成 inputs / products',output='inputs/ + products/')
        for folder,c,_ in observed: g.add_edge('materialize','component:'+c['name'],reason='generated package/contract/input boundary')
    g.add_node('integration:all',name='integrate.py',kind='integration',label=f'读取全部 {len(observed)} 个组件产物',output='outputs/core_manifest.json')
    for folder,c,_ in observed: g.add_edge('component:'+c['name'],'integration:all',reason='all component outputs collected',path=c['output'])
    g.add_node('report',name='final_report.py',kind='report',label='报告摘要与关注项',output='outputs/final_report.json')
    g.add_edge('integration:all','report',reason='core manifest read',path='outputs/core_manifest.json')
    assert nx.is_directed_acyclic_graph(g)
    assert all(nx.has_path(g,n,'report') for n in g)
    layers=[sorted(layer) for layer in nx.topological_generations(g)]
    width=max(map(len,nx.antichains(g)))
    assert [len(v) for v in layers]==audit['earliest_layer_sizes']
    assert width==audit['maximum_independent_frontier']
    reduced=nx.transitive_reduction(g)
    assert nx.transitive_closure_dag(g).edges()==nx.transitive_closure_dag(reduced).edges()
    # Actual inputs remain metadata, not executable jobs in the width/layer calculation.
    data=dict(entry_id=key,title=spec['title'],suite=spec['suite'],view='logical component execution DAG',
      component_count=len(observed),execution_node_count=len(g),full_execution_edge_count=g.number_of_edges(),reduced_execution_edge_count=reduced.number_of_edges(),
      maximum_independent_frontier=width,earliest_layer_sizes=list(map(len,layers)),execution_layers=layers,
      nodes=[dict(id=n,**g.nodes[n],local_inputs=local.get(n,[])) for n in g],
      edges=[dict(source=a,target=b,**v) for a,b,v in g.edges(data=True)],
      reduced_edges=[dict(source=a,target=b) for a,b in reduced.edges],
      source_inputs=[dict(path=p,generated=spec['suite']=='linux2',consumers=ns) for p,ns in sources.items()],
      omitted_transitive_read_edges=[dict(source=a,target=b,**v) for a,b,v in g.edges(data=True) if not reduced.has_edge(a,b)])
    return g,reduced,layers,local,data

def fonts(path=None):
    candidates=[path] if path else [r'C:\Windows\Fonts\msyh.ttc','/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    regular=next((Path(p) for p in candidates if p and Path(p).is_file()),None)
    if regular is None: raise RuntimeError('Provide --font with a Chinese-capable TrueType/OpenType font')
    return regular

def render(g,reduced,layers,local,data,folder,font):
    W=1360; header=184; step=184; bw=370; bh=116; H=header+(len(layers)-1)*step+bh+110
    # Stable layered placement, with barycenter ordering to reduce crossing.
    positions={}; rank={n:i for i,l in enumerate(layers) for n in l}
    for index,layer in enumerate(layers):
        if index:
            layer.sort(key=lambda n:(sum(positions[p][0] for p in reduced.predecessors(n))/max(1,reduced.in_degree(n)),n))
        for j,n in enumerate(layer):
            x=W/2 if len(layer)==1 else bw/2+60+(W-bw-120)*j/(len(layer)-1)
            positions[n]=(x,header+index*step)
    # Prevent clipping of labels and overlap in each row.
    for layer in layers:
        for a,b in zip(layer,layer[1:]): assert positions[b][0]-positions[a][0]>=bw+28
    scale=2; image=Image.new('RGB',(W*scale,H*scale),'white'); draw=ImageDraw.Draw(image)
    cache={}
    def f(size):
        if size not in cache: cache[size]=ImageFont.truetype(str(font),size*scale)
        return cache[size]
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title description">',
      f'<title id="title">{html.escape(data["title"])}：组件执行 DAG</title>',
      '<desc id="description">实线为执行依赖的传递约简；完整直接读取边和输入文件节点见配套 Mermaid 与 JSON。层次不代表实测耗时。</desc>',
      '<rect width="100%" height="100%" fill="white"/>',
      '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b"/></marker></defs>',
      '<g font-family="Microsoft YaHei,Noto Sans CJK SC,Arial,sans-serif">']
    def text(x,y,value,size=18,color='#172033',anchor='start'):
        anchorpil={'start':'la','middle':'ma','end':'ra'}[anchor]
        draw.text((x*scale,y*scale),value,font=f(size),fill=color,anchor=anchorpil)
        # SVG uses top-edge positioning to match Pillow's ascender anchor.
        svg.append(f'<text x="{x:.1f}" y="{y+size:.1f}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(value)}</text>')
    text(42,24,data['title']+' · 组件执行 DAG',30)
    text(42,68,data['entry_id'],18,'#475569')
    sequence=' → '.join(map(str,data['earliest_layer_sizes']))
    text(42,101,f"核心组件 {data['component_count']}   |   最大独立宽度 {data['maximum_independent_frontier']}   |   最早执行分层 {sequence}",17,'#475569')
    for j,(kind,label) in enumerate([('component','组件'),('materialize','物化屏障'),('integration','集成'),('report','最终报告')]):
        x=42+j*205; fill,stroke=COLORS[kind]
        draw.rounded_rectangle((x*scale,143*scale,(x+18)*scale,157*scale),radius=3*scale,fill=fill,outline=stroke,width=scale)
        svg.append(f'<rect x="{x}" y="143" width="18" height="14" rx="3" fill="{fill}" stroke="{stroke}"/>')
        text(x+28,137,label,16,'#475569')
    long_index=0
    for a,b in sorted(reduced.edges,key=lambda e:(rank[e[0]],e)):
        x1,y1=positions[a]; x2,y2=positions[b]; y1+=bh; y2-=3
        if rank[b]-rank[a]>1:
            side=28+long_index//2*16 if long_index%2==0 else W-28-long_index//2*16; long_index+=1
            points=[(x1,y1),(x1,y1+25),(side,y1+25),(side,y2-25),(x2,y2-25),(x2,y2)]
            path='M '+' L '.join(f'{x:.1f},{y:.1f}' for x,y in points)
        else:
            mid=(y1+y2)/2; points=[]
            for i in range(41):
                t=i/40; u=1-t
                points.append((u**3*x1+3*u*u*t*x1+3*u*t*t*x2+t**3*x2,u**3*y1+3*u*u*t*mid+3*u*t*t*mid+t**3*y2))
            path=f'M {x1:.1f},{y1:.1f} C {x1:.1f},{mid:.1f} {x2:.1f},{mid:.1f} {x2:.1f},{y2:.1f}'
        draw.line([(x*scale,y*scale) for x,y in points],fill='#64748b',width=2*scale,joint='curve')
        draw.polygon([(x2*scale,y2*scale),((x2-5)*scale,(y2-10)*scale),((x2+5)*scale,(y2-10)*scale)],fill='#64748b')
        svg.append(f'<path d="{path}" fill="none" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)"/>')
    for index,layer in enumerate(layers):
        text(42,header+index*step-23,f'L{index+1}',13,'#64748b')
        for n in layer:
            x,y=positions[n]; v=g.nodes[n]; fill,stroke=COLORS[v['kind']]
            draw.rounded_rectangle(((x-bw/2)*scale,y*scale,(x+bw/2)*scale,(y+bh)*scale),radius=10*scale,fill=fill,outline=stroke,width=2*scale)
            svg.append(f'<rect data-node="{html.escape(n)}" x="{x-bw/2:.1f}" y="{y:.1f}" width="{bw}" height="{bh}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
            lines=[(v['name'],20,'#172033'),(v['label'],17,'#334155')]
            if v['kind']=='component':
                ins=local.get(n,[]); label='input: '+Path(ins[0]).name if ins else 'input: upstream outputs'
                lines.append((label,14,'#475569'))
            else: lines.append(('生成: '+v['output'] if v['kind']=='materialize' else 'output: '+Path(v['output']).name,14,'#475569'))
            for k,(value,size,color) in enumerate(lines):
                assert draw.textlength(value,font=f(size))<= (bw-24)*scale,(n,value)
                text(x,y+12+k*32,value,size,color,'middle')
    text(42,H-66,'实线：执行 DAG 的传递约简；输入文件写在组件内，完整直接读取边见 Mermaid / JSON。',16,'#475569')
    text(42,H-38,'层次不表示实测时间；最大独立宽度不等于第一波节点数。仅供作者分析，不向被测代理提供。',15,'#475569')
    svg.extend(['</g>','</svg>'])
    write(folder.with_suffix('.svg'),'\n'.join(svg)+'\n'); ET.parse(folder.with_suffix('.svg'))
    image=image.resize((W,H),Image.Resampling.LANCZOS); image.save(folder.with_suffix('.png'),optimize=True)
    with Image.open(folder.with_suffix('.png')) as check: assert check.size==(W,H); check.verify()
    data['render_dimensions']={'width':W,'height':H}; data['png_svg_view']='transitive reduction of the execution DAG'

def mermaid(g,data):
    ids={n:'n'+str(i) for i,n in enumerate(g)}; lines=['flowchart TD']
    for n,v in g.nodes(data=True):
        label=html.escape(v['name']+'<br/>'+v['label'],quote=True).replace('&lt;br/&gt;','<br/>')
        shape=f'[["{label}"]]' if v['kind']=='materialize' else f'["{label}"]'
        lines.append(f'  {ids[n]}{shape}:::{v["kind"]}')
    for a,b in g.edges: lines.append(f'  {ids[a]} --> {ids[b]}')
    for i,source in enumerate(data['source_inputs']):
        ident='input'+str(i); lines.append(f'  {ident}[/"{source["path"]}"/]:::input')
        if source['generated']: lines.append(f'  {ids["materialize"]} -.-> {ident}')
        for consumer in source['consumers']: lines.append(f'  {ident} -.-> {ids[consumer]}')
    lines+=['  classDef component fill:#eff6ff,stroke:#2563eb,color:#172033',
      '  classDef materialize fill:#fff7ed,stroke:#c2410c,color:#172033',
      '  classDef integration fill:#f5f3ff,stroke:#7c3aed,color:#172033',
      '  classDef report fill:#ecfdf5,stroke:#047857,color:#172033',
      '  classDef input fill:#f8fafc,stroke:#94a3b8,color:#475569,stroke-dasharray:4 3']
    # Validate declarations/edges against the source projection; no dangling IDs.
    declared=set(ids.values())|{'input'+str(i) for i in range(len(data['source_inputs']))}
    for line in lines:
        match=re.fullmatch(r'  (\w+) (?:-->|-\.->) (\w+)',line)
        if match: assert set(match.groups())<=declared
    return '\n'.join(lines)+'\n'

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); parser.add_argument('--output',type=Path); parser.add_argument('--font',type=Path); args=parser.parse_args()
    root=args.root.resolve(); out=(args.output or root/'_authoring/dags').resolve(); out.mkdir(parents=True,exist_ok=True)
    specs=json.loads((root/'_authoring/task_specs.json').read_text(encoding='utf-8')); audits=json.loads((root/'_authoring/structure_audit.json').read_text(encoding='utf-8'))
    assert len(specs)==16; font=fonts(args.font); summary=[]
    intro='''# Mixed16 v3：16 个任务的组件执行 DAG

这些图用于作者分析与展示，**不得提供给被测代理**。评测只提供对应 `TASK.md` 与 `workspace/`，不要挂载 `_authoring/` 或仓库根目录。

## 图的含义

- 一节点表示一个组件或逻辑产物生成阶段；箭头表示产物/物化边界依赖。这不是实测调用轨迹，也不展开组件内部函数。
- `run_all.py` 是安排这些步骤的编排器，不作为额外的串行计算节点；focused check 和根 `check.py` 属于验收流程，不纳入产物生成 DAG。
- SVG / PNG 使用执行 DAG 的**传递约简**：省略已有间接路径的冗余直接读取边，可达关系完全相同。最终 `integrate.py` 实际仍读取全部组件产物。
- 每任务的 Mermaid 与 JSON 保留全部直接执行依赖；Mermaid 另画出原始输入文件（虚线）。SVG / PNG 在组件内标出本地输入文件，避免将数据文件误当作执行任务。
- 蓝色为组件，橙色为 Linux 物化屏障，紫色为集成，绿色为最终报告。`integrate.py domains` 与最终 `integrate.py` 是不同的逻辑调用。
- 分层为无限资源、仅考虑依赖时的最早拓扑分层，**不代表耗时或加速比**。最大独立宽度按执行节点的最大反链计算；如数仓任务宽度为4，第一层仍只有3个组件。
- 图中的算法输出（如 `critical_path` 的业务 DAG、网络路由图、组继承环）**没有展开成组件依赖**。`artifact_provenance_release` 的条件分支改变输出内容，不会跳过组件节点。

## 校验与复现

实际 `contract.json`（Linux 从物化脚本的受校验 PAYLOAD 静态提取）逐个与作者规格比对；校验无环、最终报告可达、全部读取边、传递约简可达性、分层和独立宽度。契约摘要及完整边表见每任务 JSON，汇总见 `graph_validation.json`。

生成器位于 [`../render_dags.py`](../render_dags.py)，依赖 NetworkX 和 Pillow。中文字体支持通过 `--font` 指定：

```sh
python mixed16-extension-v3/_authoring/render_dags.py --root mixed16-extension-v3
```

## 图集目录
'''
    index=[intro]; current=None
    for i,(key,spec) in enumerate(specs.items(),1):
        g,reduced,layers,local,data=graph_for(root,key,spec,audits[key]); name=key.split('/')[1]; folder=out/name
        render(g,reduced,layers,local,data,folder,font); mmd=mermaid(g,data)
        write(folder.with_suffix('.mmd'),mmd); dump(folder.with_suffix('.json'),data)
        task_path='../../tasks/'+key
        page=[f'# {i:02d}. {spec["title"]}',f'任务：`{key}`；[任务说明]({task_path}/TASK.md) · [工作区说明]({task_path}/workspace/README.md)。',
          f'核心组件 **{data["component_count"]}**；执行节点 **{data["execution_node_count"]}**；最大独立宽度 **{data["maximum_independent_frontier"]}**；最早分层 **'+ ' → '.join(map(str,data['earliest_layer_sizes']))+'**。',
          f'![{spec["title"]}组件执行DAG]({name}.svg)',
          f'[PNG]({name}.png) · [SVG]({name}.svg) · [Mermaid 源码]({name}.mmd) · [完整边表与契约摘要]({name}.json) · [图集目录](README.md)',
          '## 完整依赖图（含输入文件）','虚线连接输入文件，实线为全部直接执行依赖；因此比上方传递约简图多出冗余但真实的读取边。', '```mermaid\n'+mmd+'```',
          '## 组件与输入接口']
        for n,v in g.nodes(data=True):
            if v['kind']!='component': continue
            s=next(s for s in spec['specs'] if s['contract']['name']==v['name']); inputs=s['contract']['inputs']
            page.append(f'- `{v["folder"]}`：{v["label"]}；输入 '+ '、'.join('`'+p+'`' for p in inputs)+f'；输出 `{v["output"]}`。')
        page+=['## 边的校验说明',f'完整执行边 {data["full_execution_edge_count"]} 条；传递约简后 {data["reduced_execution_edge_count"]} 条。两者传递闭包完全相同，所有执行节点都能到达最终报告。',
          '本图只描述逻辑组件与文件接口，不要求代理按固定调度器运行；实际实现可以在满足依赖的前提下串行或并行。']
        write(folder.with_suffix('.md'),'\n\n'.join(page)+'\n')
        if current!=spec['suite']:
            current=spec['suite']; index.append('\n### '+current+'\n')
        index.append(f'- [{i:02d}. {spec["title"]} — `{name}`]({name}.md)：宽度 {data["maximum_independent_frontier"]}，分层 '+ ' → '.join(map(str,data['earliest_layer_sizes']))+'。')
        summary.append(dict(entry=key,component_count=data['component_count'],execution_node_count=len(g),full_edges=g.number_of_edges(),reduced_edges=reduced.number_of_edges(),maximum_independent_frontier=data['maximum_independent_frontier'],earliest_layer_sizes=data['earliest_layer_sizes'],contract_sources_checked=True,dag_valid=True,all_nodes_reach_report=True,transitive_reduction_preserves_reachability=True,svg_xml_valid=True,png_valid=True))
        print('RENDERED',key,flush=True)
    index.append('\n## 全部图预览\n')
    for i,(key,spec) in enumerate(specs.items(),1):
        name=key.split('/')[1]; index.append(f'\n### {i:02d}. [{spec["title"]}]({name}.md)\n\n![{spec["title"]}组件DAG]({name}.svg)\n')
    write(out/'README.md','\n'.join(index)+'\n')
    dump(out/'graph_validation.json',dict(task_count=16,all_valid=True,view='logical execution dependencies; not a runtime trace',layout='SVG/PNG transitive reduction; Mermaid/JSON retain direct edges',input_files_excluded_from_execution_metrics=True,source_manifest_sha256=sha(root/'manifest.json'),source_specs_sha256=sha(root/'_authoring/task_specs.json'),source_structure_audit_sha256=sha(root/'_authoring/structure_audit.json'),entries=summary))
    # Resolve every relative Markdown reference generated by this tool.
    for p in out.glob('*.md'):
        for ref in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if ref.startswith('../../tasks/') or ref=='../render_dags.py': continue # resolved after publication
            assert (p.parent/ref).is_file(),(p.name,ref)
    print('ALL_16_DAGS_VALIDATED',flush=True)

if __name__=='__main__': main()
