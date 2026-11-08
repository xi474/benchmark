"""Author-only diagrams derived from real contracts. Pillow is optional for PNG export."""
from __future__ import annotations
import html,json,math,textwrap
from pathlib import Path
LABELS={
'fit_members':'成员筛选与拟合记录','hard_vote':'硬加权投票','soft_vote':'概率列对齐与软投票','vote_comparison':'两路结果比较',
'segment_index':'坐标索引与旁观轴','segment_attributes':'属性优先级与冲突','segment_assemble':'按坐标装配数据',
'fstab_parse':'fstab文本解析','aix_parse':'AIX段落解析','mount_parse':'Linux mount解析','mount_merge':'来源优先归并与冲突',
'users_json':'JSON用户适配','users_csv':'CSV用户适配','users_jsonl':'JSONL用户适配','users_merge':'用户并集与冲突证据',
'group_candidates':'命中群成员候选','mail_candidates':'邮件发件人候选','shared_durations':'共同活动时长','contact_rank':'候选并集与排名',
'cancel_morning':'取消目标及前置快照','channel_directory':'联系人渠道与回退','cancel_notifications':'取消后多渠道通知',
'attachment_receipts':'附件摘要与成功回执','independent_cleanup':'独立目录清理','archive_after_send':'成功门控与归档重放',
'photo_classification':'节日分类与缺失集合','photo_migration':'照片路径迁移','photo_outbox':'迁移后附件与报告',
'panel_slots':'两场最早空档选择','panel_invitees':'邀请群成员并集','supply_selection':'库存与评分采购','panel_commit':'活动创建与联合通知',
'dinner_date':'下个星期日程','recent_contact':'最近匹配会话身份','dinner_checkout':'多属性变体与结算',
'meeting_cancel_plan':'取消范围与通知快照','seminar_ride':'研讨会提前叫车','book_purchase':'书目条件与评分',
'download_archive':'下载目录分类归档','mail_trash':'当月目标邮件清理','manager_reply':'精确邮件ID回复','workspace_commit':'作用域冲突与状态提交',
'numeric_features':'分组数值特征','category_features':'固定词表类别特征','time_features':'时间起止跨度','feature_union':'特征行键外连接',
'exception_chain':'异常因果链与抑制','portable_frames':'可移植帧及局部变量','exception_report':'异常报告重建',
'ordinary_uses':'普通表达式引用','annotation_uses':'注解中的引用','type_comment_uses':'赋值类型注释引用','import_usage_join':'作用域遮蔽与未用导入',
'overload_signatures':'重载与参数种类','parameter_docs':'复杂参数类型文档','inherited_doc':'继承文档提供者','api_documentation':'提供者命名空间合并',
'multipart_parts':'部件类型与MIME元数据','multipart_encoding':'内联与文件载荷编码','multipart_body':'边界及请求体组装',
'manifest_inventory':'文件与链接清单','manifest_selection':'有序指令及最终排除','manifest_archive':'归档大小与字节摘要',
'module_import_scan':'静态及相对导入扫描','module_dependency_closure':'循环依赖与包初始化','module_zip':'可重复ZIP载荷',
'feature_schema':'模式结构校验','feature_attachments':'嵌套附件编解码','feature_references':'分阶段引用检查','feature_snapshot':'原子快照及导出',
'playlist_replace':'完整替换及统计重建','playlist_query':'白名单条件SQL','playlist_m3u':'半入舍入M3U导出',
'marc_xml_records':'有限MARC XML读取','marc_names_titles':'作者标题与替代文字','marc_languages':'定长及分组语言代码','marc_subjects':'主题细分与次数','marc_catalog':'书目语义汇合',
'reshard_chunks':'字节保真分块','reshard_layout':'索引分块与目录布局','reshard_restore':'容量验证及精确恢复',
'eu_professors':'欧盟任职资格','department_students':'逐部门在读人数','employment_countries':'全部任职国家','university_query':'存在性条件与国家汇合',
'invoice_classification':'文本票据分类','invoice_amounts':'金额标签与精确小数','invoice_archive_summary':'字节归档与CSV汇总',
'dinner_days':'下周五闭区间日期','dinner_calendar_index':'区间及已有晚餐索引','dinner_change_plan':'冲突取消及新增计划','dinner_notifications':'受影响对象去重通知','dinner_apply':'最终日历与幂等状态'
}
def graph(t):
    nodes=[dict(id='input',label='本地输入与公开契约',kind='input')];edges=[]; owners={c['output']:c['name'] for _,c in t['components']}
    for folder,c in t['components']:
        nodes.append(dict(id=c['name'],label=LABELS[c['operation']],kind='work',folder=folder,operation=c['operation']))
        for path in c['inputs']:
            edge=(owners.get(path,'input'),c['name'])
            if edge not in edges:edges.append(edge)
    nodes.extend([dict(id='_core',label='组件结果集成',kind='work'),dict(id='_report',label='最终报告与摘要',kind='output'),dict(id='_verify',label='工作区外正式验证',kind='verify')])
    edges.extend((c['name'],'_core') for _,c in t['components']); edges.extend([('_core','_report'),('_report','_verify')])
    return dict(id=t['id'],title=t['title'],semantics='artifact_file_dependencies_not_agent_schedule',nodes=nodes,edges=[dict(source=a,target=b) for a,b in edges])
def render(g,path):
    nodes={n['id']:n for n in g['nodes']}; pending=set(nodes);levels={}
    while pending:
        ready=sorted(n for n in pending if all(e['source'] in levels for e in g['edges'] if e['target']==n))
        if not ready:raise ValueError('cyclic dependency')
        for n in ready:levels[n]=max([levels[e['source']]+1 for e in g['edges'] if e['target']==n]+[0]);pending.remove(n)
    bands={}
    for n,l in levels.items():bands.setdefault(l,[]).append(n)
    width=max(1134,max(len(v) for v in bands.values())*330+80);height=230+(max(bands)+1)*145;positions={}
    for level,ids in bands.items():
        for i,n in enumerate(ids):positions[n]=((i+.5)*width/len(ids),170+level*145)
    colors=dict(input='#f1f3f6',work='#ffffff',output='#e9f5ec',verify='#eaf2fa');svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<defs><marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill="#657786"/></marker></defs>','<rect width="100%" height="100%" fill="white"/>']
    title=g['id']+' '+g['title']; svg.append(f'<text x="35" y="45" font-size="28" font-family="Microsoft YaHei,sans-serif">{html.escape(title)}</text>');svg.append('<text x="35" y="80" font-size="17" font-family="Microsoft YaHei,sans-serif">作者资料：实际文件接口依赖；图层不代表耗时，验证分支不计作编码并行。</text>')
    lines=[]
    for i,e in enumerate(g['edges']):
        x1,y1=positions[e['source']];x2,y2=positions[e['target']]; y1+=44;y2-=44
        if levels[e['target']]-levels[e['source']]>1:
            side=17+(i%8)*6;points=[(x1,y1),(side,y1+20),(side,y2-20),(x2,y2)]
        else:points=[(x1,y1),(x2,y2)]
        lines.append((points,nodes[e['target']]['kind']=='verify'));points_s=' '.join(f'{x},{y}' for x,y in points);dash='stroke-dasharray="6 5"' if nodes[e['target']]['kind']=='verify' else ''
        svg.append(f'<polyline points="{points_s}" fill="none" stroke="#657786" {dash} stroke-width="1.3" marker-end="url(#arrow)"/>')
    for n,(x,y) in positions.items():
        label=nodes[n]['label'];svg.append(f'<rect x="{x-146}" y="{y-44}" width="292" height="88" rx="8" fill="{colors[nodes[n]["kind"]]}" stroke="#536778" stroke-width="1.5"/>');svg.append(f'<text x="{x}" y="{y+7}" font-size="21" text-anchor="middle" font-family="Microsoft YaHei,sans-serif">{html.escape(label)}</text>')
    svg.append('</svg>');path.with_suffix('.svg').write_text('\n'.join(svg),encoding='utf-8')
    from PIL import Image,ImageDraw,ImageFont
    font_path=next((p for p in [Path('C:/Windows/Fonts/msyh.ttc'),Path('/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc')] if p.is_file()),None)
    if font_path is None:raise ValueError('CJK font required to regenerate PNG')
    scale=2;im=Image.new('RGB',(width*scale,height*scale),'white');draw=ImageDraw.Draw(im);font=ImageFont.truetype(str(font_path),21*scale);small=ImageFont.truetype(str(font_path),17*scale);big=ImageFont.truetype(str(font_path),28*scale)
    draw.text((35*scale,14*scale),title,font=big,fill='#182c3a');draw.text((35*scale,60*scale),'作者资料：实际文件接口依赖；图层不代表耗时，验证分支不计作编码并行。',font=small,fill='#536778')
    for points,dashed in lines:
        points=[(int(x*scale),int(y*scale)) for x,y in points];draw.line(points,fill='#657786',width=2*scale);x,y=points[-1];px,py=points[-2];angle=math.atan2(y-py,x-px);tri=[(x,y),(x-12*scale*math.cos(angle-.35),y-12*scale*math.sin(angle-.35)),(x-12*scale*math.cos(angle+.35),y-12*scale*math.sin(angle+.35))];draw.polygon(tri,fill='#657786')
    for n,(x,y) in positions.items():
        draw.rounded_rectangle(((x-146)*scale,(y-44)*scale,(x+146)*scale,(y+44)*scale),radius=8*scale,fill=colors[nodes[n]['kind']],outline='#536778',width=2*scale); label=nodes[n]['label'];box=draw.textbbox((0,0),label,font=font);draw.text((x*scale-(box[2]-box[0])/2,y*scale-(box[3]-box[1])/2-box[1]),label,font=font,fill='#182c3a')
    im.resize((width,height),Image.Resampling.LANCZOS).save(path.with_suffix('.png'))
    mermaid=['flowchart TD']+[f'    {n["id"]}["{n["label"]}"]' for n in g['nodes']]+[f'    {e["source"]} --> {e["target"]}' for e in g['edges']];path.with_suffix('.mmd').write_text('\n'.join(mermaid)+'\n',encoding='utf-8');path.with_suffix('.json').write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
