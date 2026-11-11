import copy

def ics(events):
    return 'BEGIN:VCALENDAR\nVERSION:2.0\n'+''.join('BEGIN:VEVENT\nDTSTART:'+s+'\nDTEND:'+e+'\nEND:VEVENT\n' for s,e in events)+'END:VCALENDAR\n'

def block(data):return dict(rows=len(data),cols=len(data[0]),data=None if all(x==0 for row in data for x in row) else data)

def register_more(add,C,R,O):
    ruleA=dict(start=540,end=840,breaks=[],weekday_end={},late_buffer=None)
    ruleB=dict(start=600,end=1020,breaks=[],weekday_end={'1':990,'3':990},late_buffer=None)
    ruleC=dict(start=540,end=1020,breaks=[[720,750]],weekday_end={},late_buffer={'threshold':1005,'minutes':15})
    calendars={'alice':ics([('20240115T090000Z','20240115T103000Z')]),'bob':ics([('20240115T110000Z','20240115T120000Z')]),'carol':ics([('20240115T100000Z','20240115T110000Z')])}
    a=dict(calendars=calendars,rules={'alice':ruleA,'bob':ruleB,'carol':ruleC},days=['2024-01-15','2024-01-16'],attendees=['alice@example.com','bob@example.com','carol@example.com'])
    b=copy.deepcopy(a);b['calendars']={n:ics([]) for n in calendars}
    d=copy.deepcopy(a);d['calendars']['alice']=ics([('20240115T090000Z','20240115T140000Z')]);d['days']=['2024-01-15','2024-01-16','2024-01-17']
    cs=[]
    for person in calendars:cs.append(C(person+'_availability','calendar_availability',{'ics':R+'/calendars/'+person,'rule':R+'/rules/'+person,'days':R+'/days'},"读取有效UTC日历子集 BEGIN:VEVENT/DTSTART/DTEND。无循环/全天事件。对 days 各日从 rule.start/end（午夜后分钟）可用时段扣除既有事件和 breaks；weekday_end 可按星期0=周一缩短结束。若 late_buffer 非null且某事件结束分钟>=threshold，将该事件忙碌结束再延长指定分钟。所有区间半开；返回按开始排序的 [startUTC,endUTC]，格式 YYYYMMDDTHHMMSSZ。事件可覆盖一天，窗口保证最终有解。"))
    cs.append(C('meeting','meeting_intersection',{'alice':O('alice_availability'),'bob':O('bob_availability'),'carol':O('carol_availability'),'attendees':R+'/attendees'},"求三个人可用时间的共同交集，选择最早能容纳连续60分钟的分钟起点。返回 {start:UTC字符串,end:UTC字符串,attendees:输入列表,summary:'Team Planning Meeting'}。只以硬可行且最早为目标，软偏好不参与正式评分。",emit={'outputs/meeting_scheduled.ics':{'pointer':'','format':'ics'}}))
    add('N09','calendar_interval_intersection',cs,[a,b,d],'meeting_minute_scan',scope='沿用源题硬可用时间、午休和缓冲。只取最早硬可行会议；源题含糊的软偏好不作为隐藏要求。日历限公开 UTC VEVENT 子集。')
    add('N10','finite_group_homomorphism',[
        C('source_group','group_closure',{'generators':R+'/generators'},"generators 是同长度置换数组列表，置换表示 i→perm[i]。复合 a*b 定义为 a[b[i]]。从单位元闭包遍历，返回按置换字典序排序的全部元素列表。作用域≤5，群阶≤120。"),
        C('target_group','group_closure',{'generators':R+'/images'},"对目标生成元像使用相同置换复合规则计算目标子群并排序。"),
        C('homomorphism','homomorphism',{'source':O('source_group'),'target':O('target_group'),'generators':R+'/generators','images':R+'/images'},"检查 generators[i]→images[i] 是否定义同态。返回 {valid:false,mapping:[]} 或 {valid:true,mapping:[{source:源置换,target:目标置换},...]}，mapping按源置换字典序。不同生成词到同一源元素必须得到同一像，包含逆元形成的关系。不是单独检查每个像为合法置换。")],
        [dict(generators=[[1,2,0],[0,2,1]],images=[[1,2,0],[0,2,1]]),dict(generators=[[1,2,0],[0,2,1]],images=[[1,2,0],[1,2,0]]),dict(generators=[[1,0]],images=[[0,1]])],'group_table_exhaustive')
    matrices=[[[block([[2,0],[0,3]]),block([[0],[0]])],[block([[0,0]]),block([[0]])]],[[block([[1]]),block([[2]])],[block([[0]]),block([[1]])]],[[block([[0]]),block([[0,0]])],[block([[0],[0]]),block([[1,0],[0,2]])]]]
    add('N11','typed_zero_block_products',[
        C('block_layout','block_layout',{'matrix':R+'/matrix'},"matrix是二维块列表，每块 {rows,cols,data:整数二维列表或null}，null表示有形状的零矩阵。相同块行的rows一致，相同块列的cols一致；总体为方阵且块行列分割相同。返回 {row_sizes,col_sizes}。"),
        C('squared','block_square',{'matrix':R+'/matrix','layout':O('block_layout')},"计算 B²，返回同分块结构；每个块仍含 rows/cols。全零块 data=null，其他块 data为整数二维列表。不得折叠成无形状标量0。"),
        C('cubed','block_cube',{'squared':O('squared'),'matrix':R+'/matrix','layout':O('block_layout')},"消费 B² 再乘 B，返回 {layout:输入layout,blocks:B³的有形状分块矩阵}；使用与 squared相同零块表示。")], [dict(matrix=m) for m in matrices],'dense_block_cube')
    add('N12','foreign_key_unique_choices',[
        C('base_candidates','choice_base',{'entities':R+'/entities'},"entities=[{id:整数,name,active:bool}]。返回active=true的实体列表，保持输入顺序，不按name合并实体。"),
        C('related_matches','choice_matches',{'relations':R+'/relations','minimum':R+'/minimum'},"relations=[{entity:ID,funny:bool,weight:整数}]。返回每条 funny=true且weight>=minimum的关联记录的entity ID，保留关系顺序及重复值。条件必须在同一关联行成立。"),
        C('form_choices','choice_join',{'candidates':O('base_candidates'),'matches':O('related_matches')},"按实体身份做半连接，返回 [{id,label:name}]。每个候选最多一次，保持候选原顺序；同名不同ID仍为不同选项。")],
        [dict(entities=[dict(id=1,name='Same',active=True),dict(id=2,name='Same',active=True),dict(id=3,name='No',active=False)],relations=[dict(entity=1,funny=True,weight=5),dict(entity=1,funny=True,weight=8),dict(entity=2,funny=True,weight=4),dict(entity=3,funny=True,weight=9)],minimum=4),dict(entities=[dict(id=4,name='Four',active=True),dict(id=5,name='Five',active=True)],relations=[dict(entity=4,funny=True,weight=1),dict(entity=4,funny=False,weight=9),dict(entity=5,funny=True,weight=9)],minimum=7),dict(entities=[dict(id=7,name='Seven',active=True)],relations=[],minimum=0)],'choice_exists')
    add('N13','queued_posts_topic_merge',[
        C('exempt_users','exempt_users',{'memberships':R+'/memberships','exempt_groups':R+'/exempt_groups'},"memberships={用户ID:[组名]}；返回属于任一豁免组的用户ID，按字典序。"),
        C('initial_queue','initial_queue',{'posts':R+'/queue'},"将初始待审 posts=[{id,tid,user}] 独立拷贝，按post ID排序返回。所有引用为已知主题。"),
        C('moderation','replay_moderation',{'topics':R+'/topics','queue':O('initial_queue'),'exempt':O('exempt_users'),'events':R+'/events'},"顺序执行有限事件。post={kind:'post',id,tid,user}：豁免者直接published，否则入queue。merge={kind:'merge',sources:[活跃主题],target:另一活跃主题}：删除source主题并把所有待审/已发布帖子tid迁到target。approve={kind:'approve',id:待审post}：移到published。返回 {topics:排序活跃ID,queue:按id排序帖子,published:按id排序帖子}。不加入并发、撤销或失败重试。")],
        [dict(topics=['a','b'],queue=[dict(id='p0',tid='a',user='u')],memberships={'u':[],'admin':['staff']},exempt_groups=['staff'],events=[dict(kind='post',id='p1',tid='a',user='admin'),dict(kind='merge',sources=['a'],target='b'),dict(kind='approve',id='p0')]),dict(topics=['a','b','c'],queue=[],memberships={'u':[]},exempt_groups=[],events=[dict(kind='post',id='x',tid='a',user='u'),dict(kind='merge',sources=['a'],target='b'),dict(kind='merge',sources=['b'],target='c'),dict(kind='approve',id='x')]),dict(topics=['k'],queue=[],memberships={'u':['ok']},exempt_groups=['ok'],events=[dict(kind='post',id='z',tid='k',user='u')])],'moderation_ids')
    from blueprints_final import register_final
    register_final(add,C,R,O)
