"""Author-side task definitions and fixture generation, excluded from agent mounts."""
import copy
import json
import random
from strengthening import NEW_RULES, new_fixture

# Keep the original sixteen names; redistribute them by the original suite style.
SCENARIOS = [
('multistage4','regional_failover_readiness','跨区域故障切换','核验复制延迟、切换失败率与快照完整性，交付风险、值班分配和恢复波次','replication failover snapshots','risk_queue duty_queue recovery_waves',0),
('multistage4','warehouse_cutover_assurance','数仓切换保障','核验回填失败、数据新鲜度与校验和，生成切换风险和分批修复计划','backfill freshness checksums','cutover_risk reviewer_load repair_waves',1),
('multistage4','artifact_provenance_release','制品溯源发布','关联构建失败、签名完整性与扫描延迟，仅在出现阻断证据时生成修复波次','builds signatures scans','release_risk audit_assignment remediation_waves',2),
('multistage4','storage_tiering_migration','存储分层迁移','核验对象完整性、复制滞后和搬迁失败，平衡审核负载并计算迁移关键路径','objects replication transfers','migration_risk approval_load migration_waves',3),
('reasoning4','edge_fleet_rollout','边缘设备灰度发布','联合求解维护窗口、升级人员分配与设备依赖关键路径，生成可执行灰度计划','maintenance_windows crew_assignment rollout_order','',0),
('reasoning4','tenant_quota_rebalance','租户配额再平衡','先确定配额调整窗口与资源依赖，再在窗口和容量双约束下分配执行人员','rebalance_windows resource_order operator_assignment','',1),
('reasoning4','batch_scheduler_transition','批处理调度迁移','在带冷却期的窗口内选取迁移人员，同时计算作业关键路径和容量受限分配','calendar_windows worker_assignment job_order','',2),
('reasoning4','api_deprecation_campaign','API 下线管理','优化带预算和期限的公告覆盖，并联合人员分配精确求解资源受限下线调度','notice_windows support_assignment retirement_order','',3),
('context8','payment_settlement_reconciliation','支付清算对账','兼容新旧清算事件，按修订去重并计算对账窗口，同时关联支付链路故障','settlements settlement_windows payment_traces','',0),
('context8','identity_federation_transition','身份联邦迁移','比较声明模式并重放令牌轮换与撤销，结合组继承闭包生成授权审计','claims sessions authorization','',1),
('context8','streaming_checkpoint_recovery','流处理检查点恢复','兼容事件编码并恢复已确认的连续偏移，在缺口处停止，另行生成脱敏诊断日志','event_codec checkpoint_restore diagnostic_logs','',2),
('context8','search_index_rebuild','搜索索引重建','解析字段重命名图并恢复分片修订，按副本仲裁与预算优化索引切换','mapping_compat shard_replay cutover_plan','',3),
('linux2','certificate_rotation_readiness','证书轮换准备','物化工具并计算撤销感知的最宽信任路径，联合策略优化证书轮换覆盖','trust_graph trust_policy renewal_windows','',0),
('linux2','backup_restore_certification','备份恢复认证','物化工具并选择最优恢复链，原子重放事务以核验目标状态和恢复时限','backup_graph journal_restore backup_windows','',1),
('linux2','observability_retention_upgrade','可观测数据保留升级','物化工具并求解法律保留与分类配额背包，联合脱敏日志覆盖进行授权','archive_logs retention_windows retention_policy','',2),
('linux2','network_policy_convergence','网络策略收敛','物化工具并计算故障后的等价最短路，联合时序防火墙验证实际转发路径','route_graph firewall_policy network_traces','',3),
]

RULES = {
'failure_evidence':('修订证据失败率','输入为记录数组，每项 id:str、revision:int>=0、owner:非空str、category:prepare/copy/verify、tags:list[str]、failures:int>=0、total:int>=1、lag:int>=0、valid:bool；failures<=total。id/owner/category/tags 去首尾空白，owner/category/tags 小写，tags 去重排序。按 id 保留最大 revision；同 id 同 revision 的规范化记录冲突报 ValueError，相同记录去重。score=ceil(20*failures/total)+offset，截断到0..20。输出 {records:[{id,source,owner,category,tags,score}],count,score_total}；source=组件名，records 按(source,id)排序。空输入产生空records和零统计。'),
'lag_evidence':('修订证据延迟','输入、规范化、版本冲突和输出 schema 与失败率证据相同；score=ceil(lag/sla)+offset 后截断0..20，sla 来自契约且大于0。'),
'integrity_evidence':('修订证据完整性','输入、规范化、版本冲突和输出 schema 与失败率证据相同；score=(valid 为真时0否则15)+failures+offset 后截断0..20。'),
'risk_ranking':('风险排名','输入为证据封装对象列表，合并 result.records；以(source,id)去重，相同键记录完全一致才可合并，否则 ValueError。选 score>=threshold 的记录，按(-score,source,id)排序后保留前limit项。输出 {records,ranking:list[source+":"+id],score_total}；records 单独按(source,id)排序，空集合输出空列表与0。'),
'review_balance':('负载分配','输入为证据封装对象列表，合并去重规则同风险排名。按(-score,source,id)依次将记录分配到当前总分最低的 reviewer，总分相同取字典序最小 reviewer。输出 {records,assignments:[{id:source+":"+id,reviewer}],loads:{reviewer:总分}}；assignments 按id排序，records按(source,id)，空输入仍保留全部reviewer的零负载。'),
'remediation_plan':('依赖波次与条件修复','输入证据合并冲突规则同风险排名。category 次序为 prepare<copy<verify；每条记录依赖所有较早类别记录，duration=1+score//5，节点id=source+":"+id。only_if_blocking 为真且没有 tags含blocking且score>=threshold 的记录时，使用空节点集合。输出 {records,blocked:false,waves,critical_path,makespan,earliest_finish}；波次与关键路径规则同 critical_path。'),
'weighted_intervals':('带冷却期的加权区间选择','输入 {windows:[{id:非空str,start:int>=0,end:int>start,value:int}]}，清理后重复id报ValueError。窗口为半开区间，前一end+cooldown<=后一start才相容。最大化总value，允许选空集合和负value；平局选排序后ID元组字典序最小者。输出 {selected:按id排序列表,value:总价值}，空输入为[]和0。推荐动态规划，不能按价值贪心。'),
'capacity_assignment':('技能容量约束分配','首输入 {jobs:[{id,skill:str,duration:int>=1}],workers:[{id,skills:list[str],capacity:int>=0,cost:int>=0,affinity:{jobid:int}}]}。各数组清理后ID不得重复；ID和技能按输入有效非空文本使用。全部job必须分配到具备skill且累计duration不超过capacity的worker；先最大化affinity总和，再最小化sum(cost*duration)，最后按排序后的(job,worker)元组序打破平局。后续输入若有selected，仅保留这些worker；若有makespan，每worker容量再截断到makespan。输出 {feasible,score,cost,assignments:[{job,worker}]}，assignments按job排序。无解时false/0/0/[]；无job时true/0/0/[]。'),
'critical_path':('依赖图与确定性关键路径','首输入 {nodes:[{id:非空str,duration:int>=0,deps:list[id]}]}；重复id、重复依赖、未知依赖、自依赖或环均ValueError。每波取全部当前就绪节点并按id排序，再提交整波。earliest_finish 为最长前驱finish+duration；并列前驱或终点取完整路径ID列表字典序最小者。后续输入若为分配结果，无解时输出blocked=true及空字段；有解时给同worker的job按jobid排序后添加相邻串行依赖，新增依赖造成环也报错。正常输出 {blocked:false,waves:list[list[id]],critical_path:list[id],makespan:int,earliest_finish:{id:int}}。空图所有集合空、makespan=0。'),
'event_decode':('新旧事件编码兼容','输入 {events:list[dict或JSON字符串],checkpoints:list}。partition或旧topic为非空str；offset或旧sequence为int>=0；epoch或旧generation为int>=0，缺省0；committed或旧ack为bool，缺省false。新字段存在时优先使用新字段。输出 {events:[{partition,offset,epoch,committed}],checkpoints}；events按(partition,offset,epoch,committed)排序，保留重复给下游处理；checkpoints原样传递。非法JSON、缺字段或非法类型ValueError；空events合法。'),
'settlement_decode':('新旧清算事件兼容','输入 {events:list[dict或JSON字符串]}。读取id:str、revision:int>=0（缺省0）、ts或旧timestamp:int>=0、key或旧account:非空str、value或旧amount:有限数字。新字段优先。规范化key为小写；输出 {events:[{id,revision,ts,key,value}]} 按(id,revision,ts,key,value)排序；保留修订交下游处理。bool不能作为数值，非法JSON/非有限值/缺字段ValueError。'),
'checkpoint_replay':('连续确认偏移恢复','输入 {checkpoints:[{partition,offset:int>=-1,epoch:int>=0}],events:[{partition,offset:int>=0,epoch:int>=0,committed:bool}]}。每partition取最高epoch的checkpoint，同epoch不同offset冲突。每(partition,offset)取最高epoch事件，同epoch不同committed冲突；同内容重复允许。分区按字典序；从checkpoint.offset+1（缺省epoch=0/offset=-1）起，只重放连续、committed=true且epoch>=checkpoint.epoch的事件，遇缺口/未确认/旧epoch即停止。输出 {next_offsets:{partition:int},applied:[partition+":"+offset],pending:{partition:list[offset]}}；pending为停止位置起已有offset排序列表，applied先分区后offset。空输入输出空字典和列表。'),
'trace_correlation':('扁平与嵌套链路关联','输入 {spans:list[span]}。span含id、service非空str、duration:非负有限数字、error:bool，可有parent:id或null、children:list[span]；显式parent优先，否则嵌套父节点。展开后重复id、未知parent、环ValueError。路径duration为根到节点duration之和，不使用时间戳相减；相同duration取完整ID路径字典序最小者。输出 {error_services:小写去重排序服务列表,critical_path:list[id],duration:number,span_count:int}；空图为空列表和零。'),
'log_compatibility':('混合格式日志与脱敏','输入 {lines:list[纯文本行、JSON字符串或对象]}。纯文本首词为级别，其余为message；对象读取level或旧severity、message或旧msg。level不区分大小写，warning统一warn，只允许debug/info/warn/error。空白纯文本跳过；message必须str。将token/password/secret后等号及可选空白所连的非空值（双引号串、单引号串或直到空白/逗号/分号）替换为小写键=[REDACTED]。输出 {lines:list[大写level+空格+脱敏message],counts:{小写level:int}}；保留输入行序，空输入输出[]/{}。非法JSON、非法级别/字段ValueError。'),
'schema_compatibility':('字段模式兼容','输入 {old:list[field],new:list[field]}，field={name:非空str,type:int/float/str/bool,required:bool,default?:任意JSON值}；同一模式重复字段名ValueError。删除字段一定breaking；新增required且无default为breaking；类型变化仅int->float兼容；optional->required仅有default时兼容。输出 {compatible:bool,changes:[{field,code:removed/added/type/required,breaking:bool}]}；字段按name排序，同字段type在required之前，未变化不输出。空模式合法。'),
'event_windows':('修订去重与分桶分位数','输入 {events:[{id:非空str,revision:int>=0,ts:int>=0,key:非空str,value:有限数字}]}，key去空白小写。每id取最高revision；相同revision的规范化记录不同则ValueError，相同记录去重。按floor(ts/window_size)*window_size分桶；输出 {windows:[{start,end,key,count,sum,p95}],event_count:去重条数}，windows按(start,key)排序。p95是升序值第ceil(.95*n)项，不能插值。bool/NaN/Infinity不是合法value；空输入为[]/0。'),
'dependency_impact':('依赖传播与强连通分量','输入 {edges:list[[from:str,to:str]],seeds:list[str]}，边为有向传播方向，文本非空。重复边和seeds去重，自环和有向环合法。BFS计算seeds到可达节点最短距离；SCC覆盖所有边端点及孤立seed。输出 {distances:{id:最短边数},components:list[list[id]]}；分量内部字典序，分量列表按成员列表字典序。空图为{}/[]。非法边格式ValueError。'),
'policy_precedence':('通配策略优先级','输入 {rules:[{id,resource:通配str,action:通配str,priority:int,effect:allow/deny}],requests:[{resource:str,action:str}]}；rule id去空白后不得重复。使用区分大小写的fnmatchcase，两字段同时匹配才有效。按priority降序、resource+action中不属于*?[]的字符数降序、deny优先、id字典序选胜者；无匹配默认deny且rule_id=null。输出 {decisions:[{resource,action,effect,rule_id}],allow:int,deny:int}；decisions保留请求顺序，空输入为[]/0/0。非法规则字段ValueError。'),
}

def fixture(op,seed):
    if op in NEW_RULES: return new_fixture(op,seed)
    rng=random.Random(seed)
    if op.endswith('_evidence'):
        rows=[]
        for i in range(24+seed%5):
            rows.append(dict(id=f' R{i:03} ',revision=0,owner=[' Platform ','DATA','Security'][i%3],category=[' Prepare ','COPY','verify'][i%3],tags=[] if i%4==0 else [' Blocking ','review','blocking'],failures=i%6,total=8,lag=(i*17+seed)%300,valid=i%3!=0))
        rows.extend(copy.deepcopy(rows[:3]))
        for i in range(4):
            row=copy.deepcopy(rows[i]); row['revision']=2; row['failures']=(seed+i)%8; rows.append(row)
        rng.shuffle(rows); return rows
    if op=='weighted_intervals':
        rows=[dict(id=f'w{i}',start=i*4,end=i*4+3,value=4+(seed+i)%7) for i in range(5)]
        rows += [dict(id=f'alt{i}',start=i*3,end=i*3+6,value=(seed+i)%13-3) for i in range(10)]
        # Interval IDs intentionally match worker IDs only for w0..w4.
        rng.shuffle(rows); return {'windows':rows}
    if op=='capacity_assignment':
        jobs=[dict(id=f'j{i}',skill=['ops','data'][i%2],duration=1+(seed+i)%3) for i in range(6)]
        workers=[dict(id=f'w{i}',skills=['ops','data'] if i%2==0 else ['ops'],capacity=6+(seed+i)%4,cost=1+i%3,affinity={j['id']:(seed+i*7+k*3)%11 for k,j in enumerate(jobs)}) for i in range(5)]
        return dict(jobs=jobs,workers=workers)
    if op=='critical_path':
        return {'nodes':[dict(id=f'j{i}',duration=1+(seed+i)%5,deps=[] if i<2 else [f'j{i-2}']) for i in range(6)]}
    if op in ('event_decode','checkpoint_replay'):
        events=[]
        for part in ['east','west','cold']:
            for i in range(16):
                if i==7 and part=='east': continue
                events.append(dict(partition=part,offset=i,epoch=2,committed=not(i==9 and part=='west')))
        events+=copy.deepcopy(events[:2])
        checkpoints=[dict(partition=p,offset=seed%3,epoch=2) for p in ['east','west']]
        checkpoints.append(dict(partition='east',offset=-1,epoch=1))
        rng.shuffle(events)
        if op=='event_decode':
            for i,r in enumerate(events):
                if i%2: events[i]=json.dumps(dict(topic=r['partition'],sequence=r['offset'],generation=r['epoch'],ack=r['committed']))
        return dict(events=events,checkpoints=checkpoints)
    if op in ('event_windows','settlement_decode'):
        rows=[dict(id=f'e{i}',revision=0,ts=(i*13+seed)%240,key=[' A ','B','c'][i%3],value=(i*7+seed)%30-5) for i in range(45)]
        for i in range(6):
            row=copy.deepcopy(rows[i]); row['revision']=1; row['value']+=5; rows.append(row)
        rows+=copy.deepcopy(rows[:2]); rng.shuffle(rows)
        if op=='settlement_decode':
            for i,r in enumerate(rows):
                if i%2: rows[i]=json.dumps(dict(id=r['id'],revision=r['revision'],timestamp=r['ts'],account=r['key'],amount=r['value']))
        return dict(events=rows)
    if op=='trace_correlation':
        rows=[dict(id=f's{i:02}',service=['API','db','cache'][i%3],duration=(i*7+seed)%13,error=i%7==0,parent=None if i<2 else f's{(i-2)//2:02}') for i in range(30)]
        # One independent nested tree exercises the second encoding alongside flat spans.
        rows.append(dict(id='nested',service='gateway',duration=2,error=False,children=[dict(id='leaf',service='worker',duration=3,error=True)]))
        return dict(spans=rows)
    if op=='log_compatibility':
        lines=[]
        for i in range(35):
            level=['INFO','Error','warning','DEBUG'][i%4]; message=f'event={seed+i} token="value {i}" password=p{i}; secret = s{i}'
            lines.append(f'{level} {message}' if i%3==0 else json.dumps(dict(severity=level,msg=message)) if i%3==1 else dict(level=level,message=message))
        lines.append('   '); return dict(lines=lines)
    if op=='schema_compatibility':
        old=[dict(name=f'field{i}',type=['int','str','bool'][i%3],required=i%2==0) for i in range(12)]
        new=copy.deepcopy(old); new[0]['type']='float'; new[1]['required']=True; new[1]['default']=''
        if seed%2: new.pop(3)
        new.append(dict(name='partition',type='str',required=True,**({} if seed%3 else {'default':'default'})))
        return dict(old=old,new=new)
    if op=='dependency_impact':
        edges=[[f'n{i}',f'n{(i+1)%30}'] for i in range(28)]
        edges += [['n5','n2'],['n20','n18'],['n0','n1'],['self','self']]
        return dict(edges=edges,seeds=[f'n{seed%4}','isolated'])
    if op=='policy_precedence':
        rules=[dict(id=f'r{i:02}',resource=f'svc{i%6}/*',action='read' if i%2 else '*',priority=(seed+i)%5,effect='deny' if i%3==0 else 'allow') for i in range(24)]
        rules.extend([dict(id='exact_allow',resource='svc0/admin',action='read',priority=9,effect='allow'),dict(id='exact_deny',resource='svc0/admin',action='read',priority=9,effect='deny')])
        requests=[dict(resource=f'svc{i%8}/'+('admin' if i%3==0 else f'item{i}'),action='read' if i%2 else 'write') for i in range(40)]
        requests.append(dict(resource='svc0/admin',action='read'))
        return dict(rules=rules,requests=requests)
    raise ValueError(op)

def empty(op):
    if op in NEW_RULES:
        p=new_fixture(op,3)
        for k in ('clients','windows','nodes','events','requests','groups','rules','old','new','renames','replicas','partitions','candidates','snapshots','records','archives','edges','sources','targets','failed_nodes','failed_edges','roots','probes'):
            if k in p: p[k]=[]
        if 'minimums' in p: p['minimums']={}
        return p
    if op.endswith('_evidence'): return []
    return {'weighted_intervals':{'windows':[]},'capacity_assignment':{'jobs':[],'workers':[]},'critical_path':{'nodes':[]},
        'event_decode':{'events':[],'checkpoints':[]},'settlement_decode':{'events':[]},'checkpoint_replay':{'events':[],'checkpoints':[]},
        'trace_correlation':{'spans':[]},'log_compatibility':{'lines':[]},'schema_compatibility':{'old':[],'new':[]},
        'event_windows':{'events':[]},'dependency_impact':{'edges':[],'seeds':[]},'policy_precedence':{'rules':[],'requests':[]}}[op]

def invalid(op,seed):
    if op in NEW_RULES: return {'invalid':True}
    p=fixture(op,seed)
    if op.endswith('_evidence'):
        p[0].pop('owner'); return p
    if op=='weighted_intervals': p['windows'].append(copy.deepcopy(p['windows'][0]))
    elif op=='capacity_assignment': p['workers'][0]['capacity']=True
    elif op=='critical_path': p['nodes'][0]['deps']=['missing']
    elif op=='event_decode': p['events']=['{broken']
    elif op=='settlement_decode': p['events']=[dict(id='x',revision=0,ts=0,key='a',value=float('inf'))]
    elif op=='checkpoint_replay': p['events'][0]['offset']=-1
    elif op=='trace_correlation': p['spans'][0]['duration']=float('nan')
    elif op=='log_compatibility': p['lines']=[dict(level='FATAL',message='x')]
    elif op=='schema_compatibility': p['old'].append(copy.deepcopy(p['old'][0]))
    elif op=='event_windows': p['events'][0]['value']=float('inf')
    elif op=='dependency_impact': p['edges'].append(['bad'])
    elif op=='policy_precedence': p['rules'].append(copy.deepcopy(p['rules'][0]))
    return p

RULES.update(NEW_RULES)
