"""Author-only v3 algorithms, fixtures and exact public rules. Not agent material."""
from __future__ import annotations
import copy
import hashlib
import heapq
import itertools
import json
import math
import random
import re
from collections import defaultdict, deque
from reference import integer, number, text, obj, array, distinct, unwrap, compatibility, policy

NEW_RULES = {
'notice_coverage': ('带预算和期限的公告覆盖优化', '输入 {clients:[{id,weight:int>=0,deadline:int>=0,mandatory:bool}],windows:[{id,start:int>=0,end:int>start,cost:int>=0,clients:list[client_id]}],budget:int>=0,cooldown:int>=0}。重复ID/窗口内重复client/未知client、非法类型ValueError。选择互不重叠且前end+cooldown<=后start、总cost<=budget的窗口；仅end<=client.deadline的覆盖有效；同client价值只计一次。先要求覆盖所有mandatory客户，在可行集合中最大化覆盖weight之和、再最小化cost、最后取排序窗口ID列表字典序最小者。无可行集合返回feasible=false、空selected/completion、value/cost为0；成功输出 {feasible,selected,value,cost,completion:{client_id:最早有效公告end}}。空输入成功空解。实例窗口数<=16，不能用逐窗口价值相加的贪心替代集合覆盖。'),
'resource_cutover': ('有释放时间的精确资源受限调度', '输入顺序为本地 {nodes:[{id,client,duration:int>=1,demand:int>=1,deps:list[id]}],capacity:int>=1,horizon:int>=0}、公告notice_coverage结果、capacity_assignment结果。重复/未知/成环依赖ValueError。公告或分配不可行、任意节点client无completion或节点缺人员时，输出 {feasible:false,makespan:0,total_start:0,schedule:[]}。每节点start>=该client公告完成时间，满足所有前驱完成、同worker不可重叠、任一整数时隙sum(demand)<=capacity，end<=horizon；demand>capacity时无解。非抢占整数时刻，精确最小化makespan，再最小化sum(start)，最后按id排序后的start向量字典序取最小。输出 {feasible,makespan,total_start,schedule:[{id,start,end,worker}]}，schedule按id排序。空图可行。<=7节点，可用枚举拓扑优先序的串行最早可行插入生成器，不能仅计算无限资源关键路径。'),
'session_replay': ('乱序令牌轮换及传递撤销', '输入 {now:int>=0,events:[{id,ts:int>=0,kind:issue/refresh/revoke,token:str,...}]}，event ID唯一，按(ts,kind优先级revoke<issue<refresh,id)处理，ts>now的事件不执行但仍校验schema。issue含subject非空str、expires:int>ts、groups:list[str]；refresh含parent:str、expires:int>ts；revoke不带额外必需字段。token只能issue/refresh一次，否则ValueError。revoke可先于签发，撤销标记永久保留；刷新父令牌必须已签发、在刷新时未到期且其祖先未撤销，否则子令牌被签发但永久无效。有效refresh继承subject/groups，轮换后父令牌标为superseded且不能再次刷新；祖先之后撤销也使全部后代无效，但祖先自然到期或被轮换不使已签发子令牌失效。输出 {active_tokens:[{token,subject,groups,expires}],invalid_tokens:list[token],revoked:list[token]}；now>=expires失效，各列表按token排序，groups去重排序。缺字段、非法类型ValueError。'),
'federation_authorize': ('组继承闭包与跨组件授权', '输入顺序为 {groups:[{id,parents:list[group_id],roles:list[str]}],rules:[{id,role,resource:glob,action:glob,effect:allow/deny}],requests:[{id,token,resource,action}]}、schema_compatibility结果、session_replay结果。所有ID各自唯一，未知parent ValueError；组继承允许环，计算可达闭包直到不再增长，合并角色。只承认active_tokens；token中未知组ValueError。模式不兼容时全部deny(reason=schema)，无活动token则deny(reason=session)，否则匹配角色及区分大小写fnmatchcase资源/动作；任何deny规则优先，无deny且有allow才allow，默认deny。胜出规则按同effect中ID字典序最小者。输出 {decisions:[{id,effect,reason:schema/session/rule/default,rule_id:str或null,roles:list[str]}],allow,deny}，decisions保留请求顺序，roles排序。'),
'schema_migration': ('重命名图解析与模式迁移', '输入 {old:list[field],new:list[field],renames:[{from:str,to:str}]}，field同schema_compatibility。from唯一，重命名形成有向图，链式解析至最终名字，任何环（包括未被old字段使用的环）ValueError；不同old字段归一至同终点ValueError。将old字段重命名后，按schema_compatibility规则判断删除、增加、int->float拓宽、required/default；输出 {compatible,changes,field_map:{old_name:terminal_name}}。field_map按原字段名，changes排序同原算法；空输入可行。'),
'shard_replay': ('分片日志缺口与墓碑恢复', '输入 {replicas:[{id,shard,host,checkpoint:int>=-1,documents:[{id,version:int>=0,fields:dict}]}],events:[{replica,offset:int>=0,epoch:int>=0,op:upsert/delete,id,version:int>=0,fields:dict(仅upsert)}]}。replica ID和初始document ID分别唯一，未知replica ValueError。相同(replica,offset)取最高epoch；任意同epoch不同内容冲突ValueError，相同内容重复允许。从checkpoint+1逐个处理连续offset，首个缺口停止。每document只接受更高version；相同version相同内容幂等、不同内容（包括delete与upsert）冲突；较低version忽略，墓碑保留版本防止旧upsert复活。输出 {replicas:[{id,shard,host,applied_offset,documents:[{id,version,fields}],tombstones:{id:version},sha256}]}，副本与documents按id，摘要对documents的UTF-8紧凑sort_keys JSON计算SHA256；空副本表返回空列表。'),
'quorum_cutover': ('副本仲裁与预算最优切换', '输入顺序为 {partitions:[{id,quorum:int>=1,value:int>=0,target_sha256:str,target_offset:int>=-1}],candidates:[{id,replica,cost:int>=0}],budget:int>=0}、schema_migration结果、shard_replay结果。各数组ID唯一；未知replica或分片、同replica多个candidate、非法digest ValueError。只有摘要等于对应partition.target_sha256且applied_offset>=target_offset的副本候选可用。选择总cost<=budget的候选集合；同partition同host最多一个、每partition所选数只能为0或恰好quorum。最大化已满足partition.value总和，再最小cost，再排序candidate ID列表字典序最小。模式不兼容返回blocked=true及空选择；否则输出 {blocked:false,selected,partitions:已满足分片ID排序,value,cost}。<=14候选，需精确优化，不能逐副本贪心或用副本数量替代独立host仲裁。'),
'trust_paths': ('撤销与有效期约束的最宽信任路径', '输入 {now:int>=0,nodes:[{id,expires:int>=0,revoked:bool}],roots:list[id],edges:[{issuer,subject,expires:int>=0}]}；节点ID唯一，根/边端点必须存在，同issuer/subject重复边ValueError。删除revoked或expires<=now的节点和expires<=now的边；有向环合法。对每可达节点，选择根到它的路径，使所有节点/边expires的最小值最大；再选最少边数，再选完整ID路径字典序最小。输出 {trusted:[{id,path:list[id],valid_until:int}],untrusted:list[id]}，列表按id。不能只做最短路，也不能因某条路径被撤销而忽略仍有效替代路径。空图合法。'),
'certificate_schedule': ('受信任与策略门控的轮换覆盖', '输入顺序为notice_coverage本地schema（client ID即证书ID）、trust_paths结果、policy_precedence结果。只有trusted证书且存在该resource、action=rotate、effect=allow的策略decision才算可覆盖；其他client从每个窗口覆盖集合中排除，但mandatory义务不能删除。然后精确执行notice_coverage的期限/冷却期/预算/覆盖价值优化，返回相同schema。改变任一上游可能使原可行方案不可行，不能把deny证书仍算作已覆盖。'),
'recovery_chain': ('分叉备份链的恢复点与成本优化', '输入 {target:int>=0,snapshots:[{id,kind:full/incremental,parent:str或null,start:int>=0,end:int>start,cost:int>=0,epoch:int>=0,valid:bool,state:[{key,value:JSON值}]}]}。snapshot ID与每份state的key唯一，未知parent或任意parent环ValueError。full必须parent=null且start=0；incremental只有parent有效、parent.end==start且epoch相等才可恢复（不满足为不可恢复，不是schema错误）。valid=false的节点及其后代不可恢复；只有end<=target可选。先最大化恢复点end，再最小化整条链cost，再按路径ID列表字典序最小选一条。输出 {feasible,chain:list[id],snapshot_end:int,cost:int,state:按key排序的完整恢复点状态}；无可恢复快照时false/[]/0/0/[]。'),
'transaction_replay': ('连续LSN与原子事务重放', '输入 {checkpoint:int>=-1,records:[{lsn:int>=0,epoch:int>=0,tx:str,kind:write/commit/abort,...}]}。write含key:str、value:JSON值、seq:int>=0；commit含count:int>=0；abort无额外必需字段。每lsn取最高epoch，任意相同lsn/epoch内容冲突ValueError，相同内容去重；从checkpoint+1连续扫描，首缺口停止。按LSN积累每tx的writes；commit须seq恰为0..count-1，每key可重复并按seq覆盖，之后才一次输出原子事务；缺写commit标为incomplete，不输出部分写。abort丢弃事务。已扫描前缀内commit/abort后又出现同tx记录ValueError。输出 {watermark:int,transactions:[{tx,commit_lsn,writes:[{key,value}],duration:int}],incomplete:list[tx],incomplete_commits:[{tx,commit_lsn}]}；transactions和incomplete_commits按(commit_lsn,tx)，duration为write条数，writes按seq，incomplete含未结束/缺写事务并按tx排序。空records返回checkpoint及空集合。'),
'restore_join': ('快照与原子日志的恢复一致性核验', '输入顺序为 {target:int>=0,rto:int>=0,expected_sha256:64位小写hex}、recovery_chain结果、transaction_replay结果。要求snapshot可行、snapshot_end<=target、日志watermark>=target，且snapshot_end<commit_lsn<=target范围没有incomplete_commits。取该范围的原子事务按commit顺序应用到snapshot.state；不能应用仅有部分writes或aborted事务。耗时=备份链cost+所应用事务duration之和。输出 {feasible,reason:ok/snapshot/gap/transaction/rto/digest,applied:list[tx],state:[{key,value}],sha256:str,cost:int}，state按key；digest为state规范紧凑JSON的SHA256。snapshot/gap/transaction失败输出空applied/state、sha256为空、cost=0；其余失败保留计算结果。失败优先级为snapshot、gap、transaction、rto、digest，不能因目标摘要恰好一致而忽略缺写的已提交事务。'),
'retention_optimizer': ('法律保留与分类配额的分组背包', '输入 {archives:[{id,category,hold:bool,modes:[{id,bytes:int>=0,value:int>=0}]}],budget:int>=0,minimums:{category:int>=0}}。archive ID和同archive的mode ID唯一，空mode数组允许；每archive选择至多一个mode，hold=true必须选一个；各category选中archive数量>=minimums。总bytes<=budget，精确最大化总value，再最小bytes，再按(archive,mode)排序列表字典序最小。输出 {feasible,selected:[{archive,mode}],bytes,value}；无解false/[]/0/0。<=10档案、每个<=3模式；可以DP/回溯，不能按value/bytes贪心或删除法律保留档案。'),
'retention_audit': ('保留计划与日志覆盖联合授权', '输入顺序为 {rules:policy_precedence规则数组,requests:[{id,archive,resource,action}]}、log_compatibility结果、retention_optimizer结果。request ID唯一。脱敏后的lines以空白/行界提取request=<id>与archive=<id>标记；相同request重复出现或未知request/标记冲突ValueError。每请求按优先级依次判断：计划不可行deny(plan)，archive未保留deny(retention)，无该request且archive相同的审计行deny(audit)，否则按policy_precedence决策，reason=policy。输出 {decisions:[{id,effect,reason,rule_id}],allow,deny}，顺序同requests；不能只运行静态策略忽略保留结果或审计覆盖。'),
'ecmp_routes': ('故障后的等价最短路径集', '输入 {nodes:list[str],edges:[{from,to,weight:int>=1}],sources:list[id],targets:list[id],failed_nodes:list[id],failed_edges:list[[from,to]]}。节点ID/有向边唯一，端点/源/目标/故障节点或边必须存在；环合法。删除故障节点及边后，对所有source-target组合计算最短距离，并返回全部等价最短路径的第一跳。输出 {routes:[{source,target,distance:int或null,next_hops:list[id]}],active_edges:[{from,to,weight}]}，routes按(source,target)，next_hops排序，active_edges按(from,to)。source==target且未故障时distance=0、next_hops=[]；不可达distance=null。不能只保留Dijkstra的一条前驱。'),
'stateful_acl': ('时序连接状态与双向防火墙', '输入 {timeout:int>=1,rules:[{id,src:glob,dst:glob,protocol:tcp/udp/*,priority:int,effect:allow/deny}],events:[{id,ts:int>=0,seq:int>=0,src,dst,sport:int1..65535,dport:int1..65535,protocol:tcp/udp,flag:syn/data/fin/rst}]}。rule/event ID唯一，按(ts,seq,id)处理。会话用双向五元组标识；ts>=last_activity+timeout时失效。不存在会话时仅syn能开连接，按priority降序、src+dst+protocol非*?[]字符数降序、deny优先、id升序匹配规则，默认deny。存在有效会话则双向data/fin/rst或syn允许，更新last_activity；fin/rst后关闭。无会话的data/fin/rst拒绝。输出 {decisions:[{id,allowed:bool,reason:rule/state/no_session/default,rule_id:str或null,src,dst}],active_sessions:int}，decision按处理顺序；结束时active_sessions以最后事件时间清理超时。'),
'network_join': ('ECMP实际路径与状态决策联合核验', '输入顺序为 {probes:[{id,event,source,target,hops:list[id]}]}、ecmp_routes结果、stateful_acl结果，probe ID唯一、未知event ValueError。依次检查ACL decision.allowed及src/dst匹配（失败reason=acl），route存在且distance非null（route），hops首尾等于source/target且每条有向边在active_edges中（path），边权和等于最短distance且第一跳在next_hops内（非零路径；失败reason=non_shortest）。输出 {results:[{id,reachable:bool,reason:ok/acl/route/path/non_shortest}],reachable_count}，结果保留probe顺序。不能只相信静态可达或只看ACL放行。'),
}

def canonical(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def coverage(p):
    clients=array(p['clients']); rows=array(p['windows']); distinct(clients); distinct(rows)
    budget=integer(p['budget'],0); cooldown=integer(p['cooldown'],0); clients={text(r['id']):r for r in clients}
    for r in clients.values():
        integer(r['weight'],0); integer(r['deadline'],0)
        if type(r['mandatory']) is not bool: raise ValueError('mandatory')
    for w in rows:
        integer(w['start'],0); integer(w['end'],0); integer(w['cost'],0)
        if w['end']<=w['start'] or len(set(array(w['clients'])))!=len(w['clients']) or any(x not in clients for x in w['clients']): raise ValueError('window')
    best=None
    for bits in itertools.product((0,1),repeat=len(rows)):
        chosen=[w for w,b in zip(rows,bits) if b]; cost=sum(w['cost'] for w in chosen)
        if cost>budget: continue
        ordered=sorted(chosen,key=lambda w:(w['start'],w['end'],w['id']))
        if any(a['end']+cooldown>b['start'] for a,b in zip(ordered,ordered[1:])): continue
        completed={}
        for w in chosen:
            for ident in w['clients']:
                if w['end']<=clients[ident]['deadline']: completed[ident]=min(completed.get(ident,w['end']),w['end'])
        if any(r['mandatory'] and n not in completed for n,r in clients.items()): continue
        value=sum(clients[n]['weight'] for n in completed); ids=sorted(w['id'] for w in chosen); key=(-value,cost,ids)
        if best is None or key<best[0]: best=(key,dict(feasible=True,selected=ids,value=value,cost=cost,completion=dict(sorted(completed.items()))))
    return best[1] if best else dict(feasible=False,selected=[],value=0,cost=0,completion={})

def resource_schedule(p,notice,staff):
    rows=array(p['nodes']); distinct(rows); nodes={r['id']:r for r in rows}; capacity=integer(p['capacity'],1); horizon=integer(p['horizon'],0)
    for n,r in nodes.items():
        text(r['client']); integer(r['duration'],1); integer(r['demand'],1)
        if len(set(array(r['deps'])))!=len(r['deps']) or any(d not in nodes for d in r['deps']): raise ValueError('deps')
    done=set()
    while len(done)<len(nodes):
        ready={n for n,r in nodes.items() if n not in done and set(r['deps'])<=done}
        if not ready: raise ValueError('cycle')
        done|=ready
    failed=dict(feasible=False,makespan=0,total_start=0,schedule=[])
    assignments={a['job']:a['worker'] for a in staff['assignments']}
    if not notice['feasible'] or not staff['feasible'] or any(n not in assignments or r['client'] not in notice['completion'] or r['demand']>capacity for n,r in nodes.items()): return failed
    best=None
    def visit(placed,usage):
        nonlocal best
        if len(placed)==len(nodes):
            schedule=[dict(id=n,start=placed[n],end=placed[n]+nodes[n]['duration'],worker=assignments[n]) for n in sorted(nodes)]
            makespan=max((r['end'] for r in schedule),default=0); total=sum(placed.values()); key=(makespan,total,tuple(placed[n] for n in sorted(nodes)))
            if best is None or key<best[0]: best=(key,dict(feasible=True,makespan=makespan,total_start=total,schedule=schedule))
            return
        for n in sorted(nodes):
            r=nodes[n]
            if n in placed or any(d not in placed for d in r['deps']): continue
            start=max([notice['completion'][r['client']]]+[placed[d]+nodes[d]['duration'] for d in r['deps']])
            while start+r['duration']<=horizon:
                slots=range(start,start+r['duration'])
                resource=all(usage[t]+r['demand']<=capacity for t in slots)
                worker=all(assignments[j]!=assignments[n] or start+r['duration']<=s or s+nodes[j]['duration']<=start for j,s in placed.items())
                if resource and worker: break
                start+=1
            else: continue
            if best and start+r['duration']>best[0][0]: continue
            placed[n]=start
            for t in range(start,start+r['duration']): usage[t]+=r['demand']
            visit(placed,usage)
            for t in range(start,start+r['duration']): usage[t]-=r['demand']
            del placed[n]
    visit({},[0]*horizon)
    return best[1] if best else failed

def sessions(p):
    now=integer(p['now'],0); events=array(p['events']); distinct(events); tokens={}; revoked=set(); superseded=set()
    issued=set()
    for e in events:
        text(e['token']); integer(e['ts'],0)
        if e['kind'] not in ('issue','refresh','revoke'): raise ValueError('kind')
        if e['kind']=='issue':
            text(e['subject']); [text(g) for g in array(e['groups'])]
        if e['kind']=='refresh': text(e['parent'])
        if e['kind']!='revoke' and integer(e['expires'],0)<=e['ts']: raise ValueError('expiry')
        if e['kind']!='revoke':
            if e['token'] in issued: raise ValueError('duplicate token')
            issued.add(e['token'])
    def ancestor_revoked(token):
        seen=set()
        while token is not None:
            if token in revoked: return True
            if token in seen: raise ValueError('token cycle')
            seen.add(token); token=tokens.get(token,{}).get('parent')
        return False
    priority={'revoke':0,'issue':1,'refresh':2}
    for e in sorted(events,key=lambda e:(e['ts'],priority[e['kind']],e['id'])):
        if e['ts']>now: continue
        token=e['token']
        if e['kind']=='revoke': revoked.add(token); continue
        if token in tokens: raise ValueError('duplicate token')
        if e['kind']=='issue':
            tokens[token]=dict(subject=e['subject'],groups=sorted(set(e['groups'])),expires=e['expires'],parent=None,valid=not ancestor_revoked(token))
        else:
            parent=e['parent']; r=tokens.get(parent); valid=bool(r and r['valid'] and parent not in superseded and r['expires']>e['ts'] and not ancestor_revoked(parent) and not ancestor_revoked(token))
            tokens[token]=dict(subject=r['subject'] if r else '',groups=r['groups'][:] if r else [],expires=e['expires'],parent=parent,valid=valid)
            if valid: superseded.add(parent)
    active=[]; invalid=[]
    for token,r in sorted(tokens.items()):
        if r['valid'] and token not in superseded and now<r['expires'] and not ancestor_revoked(token):
            active.append(dict(token=token,subject=r['subject'],groups=r['groups'],expires=r['expires']))
        else: invalid.append(token)
    return dict(active_tokens=active,invalid_tokens=invalid,revoked=sorted(revoked))

def authorize(p,schema,state):
    import fnmatch
    groups=array(p['groups']); rules=array(p['rules']); requests=array(p['requests']); distinct(groups); distinct(rules); distinct(requests)
    groups={r['id']:r for r in groups}
    for r in groups.values():
        for g in array(r['parents']):
            if g not in groups: raise ValueError('unknown group')
        for role in array(r['roles']): text(role)
    for r in rules:
        for k in ('role','resource','action'): text(r[k])
        if r['effect'] not in ('allow','deny'): raise ValueError('effect')
    active={t['token']:t for t in state['active_tokens']}; result=[]
    for t in active.values():
        if any(g not in groups for g in t['groups']): raise ValueError('unknown token group')
    for req in requests:
        for k in ('token','resource','action'): text(req[k])
        roles=set(); rule=None; effect='deny'
        if not schema['compatible']: reason='schema'
        elif req['token'] not in active: reason='session'
        else:
            pending=list(active[req['token']]['groups']); visited=set()
            while pending:
                g=pending.pop()
                if g in visited: continue
                visited.add(g); roles.update(groups[g]['roles']); pending.extend(groups[g]['parents'])
            matches=[r for r in rules if r['role'] in roles and fnmatch.fnmatchcase(req['resource'],r['resource']) and fnmatch.fnmatchcase(req['action'],r['action'])]
            if matches:
                winner=min(matches,key=lambda r:(r['effect']!='deny',r['id'])); rule=winner['id']; effect=winner['effect']; reason='rule'
            else: reason='default'
        result.append(dict(id=req['id'],effect=effect,reason=reason,rule_id=rule,roles=sorted(roles)))
    return dict(decisions=result,allow=sum(r['effect']=='allow' for r in result),deny=sum(r['effect']=='deny' for r in result))

def schema_migration(p):
    renames={}
    for r in array(p['renames']):
        a=text(r['from']); b=text(r['to'])
        if a in renames: raise ValueError('duplicate rename')
        renames[a]=b
    def terminal(n):
        seen=set()
        while n in renames:
            if n in seen: raise ValueError('rename cycle')
            seen.add(n); n=renames[n]
        return n
    for n in renames: terminal(n)
    mapping={text(r['name']):terminal(text(r['name'])) for r in array(p['old'])}
    if len(set(mapping.values()))!=len(mapping): raise ValueError('rename collision')
    old=[dict(r,name=mapping[r['name']]) for r in p['old']]
    return dict(**compatibility(dict(old=old,new=p['new'])),field_map=dict(sorted(mapping.items())))

def replay_shards(p):
    reps=array(p['replicas']); distinct(reps); reps={r['id']:r for r in reps}; versions={}; highest={}
    for r in reps.values():
        text(r['shard']); text(r['host']); integer(r['checkpoint'],-1); docs=array(r['documents']); distinct(docs)
        for doc in docs: integer(doc['version'],0); obj(doc['fields'])
    for e in array(p['events']):
        if e['replica'] not in reps: raise ValueError('unknown replica')
        integer(e['offset'],0); integer(e['epoch'],0); text(e['id']); integer(e['version'],0)
        if e['op'] not in ('upsert','delete'): raise ValueError('op')
        if e['op']=='upsert': obj(e['fields'])
        k=(e['replica'],e['offset'],e['epoch'])
        if k in versions and versions[k]!=e: raise ValueError('offset conflict')
        versions[k]=e; key=k[:2]
        if key not in highest or e['epoch']>highest[key]['epoch']: highest[key]=e
    results=[]
    for ident,r in sorted(reps.items()):
        state={d['id']:(d['version'],copy.deepcopy(d['fields'])) for d in r['documents']}; offset=r['checkpoint']
        while (ident,offset+1) in highest:
            offset+=1; e=highest[ident,offset]; val=(e['version'],copy.deepcopy(e['fields']) if e['op']=='upsert' else None)
            previous=state.get(e['id'])
            if previous and previous[0]==val[0] and previous!=val: raise ValueError('document conflict')
            if previous is None or val[0]>previous[0]: state[e['id']]=val
        docs=[dict(id=k,version=v,fields=f) for k,(v,f) in sorted(state.items()) if f is not None]
        results.append(dict(id=ident,shard=r['shard'],host=r['host'],applied_offset=offset,documents=docs,tombstones={k:v for k,(v,f) in sorted(state.items()) if f is None},sha256=canonical(docs)))
    return dict(replicas=results)

def quorum(p,schema,replay):
    parts=array(p['partitions']); candidates=array(p['candidates']); distinct(parts); distinct(candidates); budget=integer(p['budget'],0)
    parts={r['id']:r for r in parts}; replicas={r['id']:r for r in replay['replicas']}; seen=set()
    for r in parts.values():
        integer(r['quorum'],1); integer(r['value'],0); integer(r['target_offset'],-1)
        if not re.fullmatch('[0-9a-f]{64}',r['target_sha256']): raise ValueError('digest')
    eligible=[]
    for r in candidates:
        integer(r['cost'],0)
        if r['replica'] not in replicas or r['replica'] in seen: raise ValueError('replica')
        seen.add(r['replica']); rep=replicas[r['replica']]
        if rep['shard'] not in parts: raise ValueError('partition')
        target=parts[rep['shard']]
        if rep['sha256']==target['target_sha256'] and rep['applied_offset']>=target['target_offset']: eligible.append(r)
    if not schema['compatible']: return dict(blocked=True,selected=[],partitions=[],value=0,cost=0)
    best=None
    for bits in itertools.product((0,1),repeat=len(eligible)):
        chosen=[r for r,b in zip(eligible,bits) if b]; cost=sum(r['cost'] for r in chosen)
        if cost>budget: continue
        hosts=set(); counts=defaultdict(int); okay=True
        for r in chosen:
            rep=replicas[r['replica']]; key=(rep['shard'],rep['host'])
            if key in hosts: okay=False; break
            hosts.add(key); counts[rep['shard']]+=1
        if not okay or any(n!=parts[k]['quorum'] for k,n in counts.items()): continue
        names=sorted(counts); value=sum(parts[k]['value'] for k in names); ids=sorted(r['id'] for r in chosen); key=(-value,cost,ids)
        if best is None or key<best[0]: best=(key,dict(blocked=False,selected=ids,partitions=names,value=value,cost=cost))
    return best[1]

def trust(p):
    now=integer(p['now'],0); nodes=array(p['nodes']); distinct(nodes); nodes={r['id']:r for r in nodes}; roots=array(p['roots']); edges=array(p['edges']); seen=set(); adj=defaultdict(list)
    for r in nodes.values():
        integer(r['expires'],0)
        if type(r['revoked']) is not bool: raise ValueError('revoked')
    if any(r not in nodes for r in roots): raise ValueError('root')
    for e in edges:
        a=e['issuer']; b=e['subject']; integer(e['expires'],0)
        if a not in nodes or b not in nodes or (a,b) in seen: raise ValueError('edge')
        seen.add((a,b))
        if not nodes[a]['revoked'] and not nodes[b]['revoked'] and min(nodes[a]['expires'],nodes[b]['expires'],e['expires'])>now: adj[a].append((b,e['expires']))
    widths={}; heap=[]
    for root in set(roots):
        r=nodes[root]
        if not r['revoked'] and r['expires']>now: widths[root]=r['expires']; heapq.heappush(heap,(-r['expires'],root))
    while heap:
        negative,a=heapq.heappop(heap); value=-negative
        if widths[a]!=value: continue
        for b,expiry in adj[a]:
            candidate=min(value,expiry,nodes[b]['expires'])
            if candidate>widths.get(b,-1): widths[b]=candidate; heapq.heappush(heap,(-candidate,b))
    results=[]
    for target,threshold in sorted(widths.items()):
        # Reconstruct shortest lex path in the threshold-induced subgraph.
        paths={}; queue=[]
        for root in sorted(set(roots)):
            if not nodes[root]['revoked'] and nodes[root]['expires']>=threshold and nodes[root]['expires']>now: heapq.heappush(queue,(0,(root,),root))
        while queue:
            length,path,a=heapq.heappop(queue)
            if a in paths: continue
            paths[a]=list(path)
            for b,expiry in adj[a]:
                if expiry>=threshold and nodes[b]['expires']>=threshold and b not in paths: heapq.heappush(queue,(length+1,path+(b,),b))
        results.append(dict(id=target,path=paths[target],valid_until=threshold))
    return dict(trusted=results,untrusted=sorted(set(nodes)-set(widths)))

def certificate_schedule(p,paths,decisions):
    coverage(p)  # Validate the original data before filtering; invalid IDs must not disappear.
    eligible={r['id'] for r in paths['trusted']} & {r['resource'] for r in decisions['decisions'] if r['action']=='rotate' and r['effect']=='allow'}
    data=copy.deepcopy(p)
    for w in data['windows']: w['clients']=[n for n in w['clients'] if n in eligible]
    return coverage(data)

def recovery(p):
    target=integer(p['target'],0); snapshots=array(p['snapshots']); distinct(snapshots); nodes={r['id']:r for r in snapshots}; checked={}; active=set()
    for r in nodes.values():
        for k in ('start','end','cost','epoch'): integer(r[k],0)
        if type(r['valid']) is not bool or r['end']<=r['start'] or r['kind'] not in ('full','incremental'): raise ValueError('snapshot')
        state=array(r['state']); keys=[text(v['key']) for v in state]
        if len(set(keys))!=len(keys): raise ValueError('state key')
        for v in state: v['value']
        if r['kind']=='full' and (r['parent'] is not None or r['start']!=0): raise ValueError('full')
        if r['parent'] is not None and r['parent'] not in nodes: raise ValueError('parent')
    def visit(n):
        if n in active: raise ValueError('snapshot cycle')
        if n in checked: return checked[n]
        active.add(n); r=nodes[n]; parent=visit(r['parent']) if r['parent'] is not None else None
        if r['kind']=='full': result=([n],r['cost']) if r['valid'] else None
        else:
            base=nodes[r['parent']] if r['parent'] else None
            result=(parent[0]+[n],parent[1]+r['cost']) if r['valid'] and parent and base['end']==r['start'] and base['epoch']==r['epoch'] else None
        active.remove(n); checked[n]=result; return result
    choices=[]
    for n,r in nodes.items():
        chain=visit(n)
        if chain and r['end']<=target: choices.append((-r['end'],chain[1],chain[0],n))
    if not choices: return dict(feasible=False,chain=[],snapshot_end=0,cost=0,state=[])
    _,cost,chain,n=min(choices); return dict(feasible=True,chain=chain,snapshot_end=nodes[n]['end'],cost=cost,state=sorted(copy.deepcopy(nodes[n]['state']),key=lambda r:r['key']))

def transactions(p):
    checkpoint=integer(p['checkpoint'],-1); allversions={}; latest={}
    for r in array(p['records']):
        integer(r['lsn'],0); integer(r['epoch'],0); text(r['tx'])
        if r['kind'] not in ('write','commit','abort'): raise ValueError('kind')
        if r['kind']=='write': text(r['key']); integer(r['seq'],0); r['value']
        if r['kind']=='commit': integer(r['count'],0)
        key=(r['lsn'],r['epoch'])
        if key in allversions and allversions[key]!=r: raise ValueError('LSN conflict')
        allversions[key]=r
        if r['lsn'] not in latest or r['epoch']>latest[r['lsn']]['epoch']: latest[r['lsn']]=r
    pending=defaultdict(list); ended=set(); incomplete=set(); incomplete_commits=[]; output=[]; watermark=checkpoint
    while watermark+1 in latest:
        watermark+=1; r=latest[watermark]; tx=r['tx']
        if tx in ended: raise ValueError('transaction after end')
        if r['kind']=='write': pending[tx].append(r)
        elif r['kind']=='abort': pending.pop(tx,None); ended.add(tx)
        else:
            writes=sorted(pending.pop(tx,[]),key=lambda w:w['seq']); ended.add(tx)
            if [w['seq'] for w in writes]!=list(range(r['count'])):
                incomplete.add(tx); incomplete_commits.append(dict(tx=tx,commit_lsn=watermark)); continue
            output.append(dict(tx=tx,commit_lsn=watermark,writes=[dict(key=w['key'],value=w['value']) for w in writes],duration=len(writes)))
    return dict(watermark=watermark,transactions=output,incomplete=sorted(set(pending)|incomplete),incomplete_commits=incomplete_commits)

def restore(p,base,log):
    target=integer(p['target'],0); rto=integer(p['rto'],0)
    if not re.fullmatch('[0-9a-f]{64}',p['expected_sha256']): raise ValueError('digest')
    def fail(reason): return dict(feasible=False,reason=reason,applied=[],state=[],sha256='',cost=0)
    if not base['feasible'] or base['snapshot_end']>target: return fail('snapshot')
    if log['watermark']<target: return fail('gap')
    if any(base['snapshot_end']<r['commit_lsn']<=target for r in log['incomplete_commits']): return fail('transaction')
    data={r['key']:copy.deepcopy(r['value']) for r in base['state']}; applied=[]; cost=base['cost']
    for tx in sorted(log['transactions'],key=lambda r:(r['commit_lsn'],r['tx'])):
        if base['snapshot_end']<tx['commit_lsn']<=target:
            applied.append(tx['tx']); cost+=tx['duration']
            for w in tx['writes']: data[w['key']]=copy.deepcopy(w['value'])
    state=[dict(key=k,value=v) for k,v in sorted(data.items())]; sha=canonical(state)
    reason='rto' if cost>rto else 'digest' if sha!=p['expected_sha256'] else 'ok'
    return dict(feasible=reason=='ok',reason=reason,applied=applied,state=state,sha256=sha,cost=cost)

def retention(p):
    archives=array(p['archives']); distinct(archives); budget=integer(p['budget'],0); minimums=obj(p['minimums'])
    for k,v in minimums.items(): text(k); integer(v,0)
    archives=sorted(archives,key=lambda r:r['id'])
    for r in archives:
        text(r['category']); distinct(array(r['modes']))
        if type(r['hold']) is not bool: raise ValueError('hold')
        for mode in r['modes']: integer(mode['bytes'],0); integer(mode['value'],0)
    best=None
    def visit(i,selected,size,value,counts):
        nonlocal best
        if size>budget: return
        if i==len(archives):
            if any(counts[k]<v for k,v in minimums.items()): return
            key=(-value,size,tuple(selected))
            if best is None or key<best[0]: best=(key,dict(feasible=True,selected=[dict(archive=a,mode=m) for a,m in selected],bytes=size,value=value))
            return
        r=archives[i]
        if not r['hold']: visit(i+1,selected,size,value,counts)
        for mode in sorted(r['modes'],key=lambda m:m['id']):
            counts[r['category']]+=1; visit(i+1,selected+[(r['id'],mode['id'])],size+mode['bytes'],value+mode['value'],counts); counts[r['category']]-=1
    visit(0,[],0,0,defaultdict(int))
    return best[1] if best else dict(feasible=False,selected=[],bytes=0,value=0)

def retention_audit(p,logs,plan):
    requests=array(p['requests']); distinct(requests); byid={r['id']:r for r in requests}; seen={}
    for r in requests:
        for k in ('archive','resource','action'): text(r[k])
    for line in logs['lines']:
        ident=re.search(r'(?:^|\s)request=([^\s]+)(?:\s|$)',line); archive=re.search(r'(?:^|\s)archive=([^\s]+)(?:\s|$)',line)
        if not ident: continue
        ident=ident.group(1)
        if ident not in byid or ident in seen or not archive or byid[ident]['archive']!=archive.group(1): raise ValueError('audit marker')
        seen[ident]=archive.group(1)
    decisions=policy(dict(rules=p['rules'],requests=[dict(resource=r['resource'],action=r['action']) for r in requests]))['decisions']; kept={r['archive'] for r in plan['selected']}; out=[]
    for req,d in zip(requests,decisions):
        reason='plan' if not plan['feasible'] else 'retention' if req['archive'] not in kept else 'audit' if req['id'] not in seen else 'policy'
        out.append(dict(id=req['id'],effect=d['effect'] if reason=='policy' else 'deny',reason=reason,rule_id=d['rule_id'] if reason=='policy' else None))
    return dict(decisions=out,allow=sum(r['effect']=='allow' for r in out),deny=sum(r['effect']=='deny' for r in out))

def routes(p):
    nodes=array(p['nodes']); ids=[text(n) for n in nodes]
    if len(ids)!=len(set(ids)): raise ValueError('nodes')
    nodes=set(ids); edges=array(p['edges']); table={}
    for r in edges:
        integer(r['weight'],1); pair=(r['from'],r['to'])
        if r['from'] not in nodes or r['to'] not in nodes or pair in table: raise ValueError('edge')
        table[pair]=r['weight']
    sources=array(p['sources']); targets=array(p['targets']); failed=set(array(p['failed_nodes'])); failed_edges=set()
    if any(n not in nodes for n in sources+targets+list(failed)): raise ValueError('node reference')
    for edge in array(p['failed_edges']):
        if len(array(edge))!=2 or tuple(edge) not in table: raise ValueError('failed edge')
        failed_edges.add(tuple(edge))
    active=[dict(r) for r in edges if (r['from'],r['to']) not in failed_edges and r['from'] not in failed and r['to'] not in failed]; reverse=defaultdict(list); adj=defaultdict(list)
    for r in active: reverse[r['to']].append((r['from'],r['weight'])); adj[r['from']].append((r['to'],r['weight']))
    result=[]
    for target in sorted(set(targets)):
        distance={} if target in failed else {target:0}; heap=[] if target in failed else [(0,target)]
        while heap:
            d,a=heapq.heappop(heap)
            if distance[a]!=d: continue
            for b,w in reverse[a]:
                if d+w<distance.get(b,math.inf): distance[b]=d+w; heapq.heappush(heap,(d+w,b))
        for source in sorted(set(sources)):
            d=distance.get(source); hops=sorted(b for b,w in adj[source] if b in distance and d==w+distance[b]) if d is not None and d!=0 else []
            result.append(dict(source=source,target=target,distance=d,next_hops=hops))
    return dict(routes=sorted(result,key=lambda r:(r['source'],r['target'])),active_edges=sorted(active,key=lambda r:(r['from'],r['to'])))

def acl(p):
    import fnmatch
    timeout=integer(p['timeout'],1); rules=array(p['rules']); events=array(p['events']); distinct(rules); distinct(events); state={}; decisions=[]
    for r in rules:
        integer(r['priority']); text(r['src']); text(r['dst'])
        if r['protocol'] not in ('tcp','udp','*') or r['effect'] not in ('allow','deny'): raise ValueError('rule')
    for r in events:
        integer(r['ts'],0); integer(r['seq'],0); text(r['src']); text(r['dst'])
        for k in ('sport','dport'):
            if integer(r[k],1)>65535: raise ValueError('port')
        if r['protocol'] not in ('tcp','udp') or r['flag'] not in ('syn','data','fin','rst'): raise ValueError('packet')
    for e in sorted(events,key=lambda e:(e['ts'],e['seq'],e['id'])):
        state={k:v for k,v in state.items() if e['ts']<v+timeout}
        endpoints=tuple(sorted(((e['src'],e['sport']),(e['dst'],e['dport'])))); key=(e['protocol'],endpoints); rule=None
        if key in state: allowed=True; reason='state'
        elif e['flag']!='syn': allowed=False; reason='no_session'
        else:
            matches=[r for r in rules if fnmatch.fnmatchcase(e['src'],r['src']) and fnmatch.fnmatchcase(e['dst'],r['dst']) and r['protocol'] in ('*',e['protocol'])]
            if matches:
                winner=min(matches,key=lambda r:(-r['priority'],-sum(c not in '*?[]' for c in r['src']+r['dst']+r['protocol']),r['effect']!='deny',r['id'])); allowed=winner['effect']=='allow'; reason='rule'; rule=winner['id']
            else: allowed=False; reason='default'
        if allowed:
            if e['flag'] in ('fin','rst'): state.pop(key,None)
            else: state[key]=e['ts']
        decisions.append(dict(id=e['id'],allowed=allowed,reason=reason,rule_id=rule,src=e['src'],dst=e['dst']))
    return dict(decisions=decisions,active_sessions=len(state))

def network(p,route,decision):
    probes=array(p['probes']); distinct(probes); decisions={r['id']:r for r in decision['decisions']}; routes={(r['source'],r['target']):r for r in route['routes']}; edges={(r['from'],r['to']):r['weight'] for r in route['active_edges']}; result=[]
    for r in probes:
        if r['event'] not in decisions: raise ValueError('event')
        d=decisions[r['event']]; target=routes.get((r['source'],r['target'])); hops=array(r['hops'])
        if not d['allowed'] or d['src']!=r['source'] or d['dst']!=r['target']: reason='acl'
        elif target is None or target['distance'] is None: reason='route'
        elif not hops or hops[0]!=r['source'] or hops[-1]!=r['target'] or any((a,b) not in edges for a,b in zip(hops,hops[1:])): reason='path'
        elif sum(edges[a,b] for a,b in zip(hops,hops[1:]))!=target['distance'] or (target['distance']!=0 and (len(hops)<2 or hops[1] not in target['next_hops'])): reason='non_shortest'
        else: reason='ok'
        result.append(dict(id=r['id'],reachable=reason=='ok',reason=reason))
    return dict(results=result,reachable_count=sum(r['reachable'] for r in result))

def evaluate_new(payloads,c):
    def validate_json(value):
        if isinstance(value,float) and not math.isfinite(value): raise ValueError('non-finite JSON')
        if isinstance(value,dict):
            for v in value.values(): validate_json(v)
        elif isinstance(value,list):
            for v in value: validate_json(v)
    validate_json(payloads)
    op=c['operation']; p=unwrap(payloads[0]); extras=[unwrap(v) for v in payloads[1:]]
    arities={'resource_cutover':2,'federation_authorize':2,'quorum_cutover':2,'certificate_schedule':2,'restore_join':2,'retention_audit':2,'network_join':2}
    if op in arities and len(extras)!=arities[op]: raise ValueError('missing dependency')
    if op=='notice_coverage': return coverage(p)
    if op=='resource_cutover': return resource_schedule(p,*extras)
    if op=='session_replay': return sessions(p)
    if op=='federation_authorize': return authorize(p,*extras)
    if op=='schema_migration': return schema_migration(p)
    if op=='shard_replay': return replay_shards(p)
    if op=='quorum_cutover': return quorum(p,*extras)
    if op=='trust_paths': return trust(p)
    if op=='certificate_schedule': return certificate_schedule(p,*extras)
    if op=='recovery_chain': return recovery(p)
    if op=='transaction_replay': return transactions(p)
    if op=='restore_join': return restore(p,*extras)
    if op=='retention_optimizer': return retention(p)
    if op=='retention_audit': return retention_audit(p,*extras)
    if op=='ecmp_routes': return routes(p)
    if op=='stateful_acl': return acl(p)
    if op=='network_join': return network(p,*extras)
    raise ValueError(op)

TARGETS={
 'api_deprecation_campaign','identity_federation_transition','search_index_rebuild',
 'certificate_rotation_readiness','backup_restore_certification','observability_retention_upgrade','network_policy_convergence',
}

def new_fixture(op,seed):
    rng=random.Random(seed); shift=seed%4
    if op in ('notice_coverage','certificate_schedule'):
        prefix='cert' if op=='certificate_schedule' else 'j'
        ids=[prefix+str(i) for i in range(6)]
        clients=[dict(id=n,weight=2+(i+seed)%7,deadline=12,mandatory=i<5 if prefix=='cert' else True) for i,n in enumerate(ids)]
        rows=[dict(id='all_fast',start=0,end=4,cost=6,clients=ids[:]),
          dict(id='first_half',start=0,end=2,cost=2,clients=ids[:3]),dict(id='second_half',start=4,end=6,cost=2,clients=ids[3:]),
          dict(id='overlap',start=1,end=5,cost=3,clients=ids[1:5]),dict(id='late',start=10,end=14,cost=1,clients=ids[:]),
          dict(id='tail',start=7,end=9,cost=2,clients=ids[3:]),dict(id='single',start=0,end=1,cost=1,clients=ids[:1]),
          dict(id='expensive',start=0,end=2,cost=10,clients=ids[:])]
        rng.shuffle(rows); return dict(clients=clients,windows=rows,budget=8+seed%3,cooldown=1)
    if op=='resource_cutover':
        return dict(nodes=[dict(id=f'j{i}',client=f'j{i}',duration=1+(seed+i)%3,demand=1+i%2,deps=[] if i<2 else [f'j{i-2}']) for i in range(6)],capacity=3,horizon=28)
    if op=='session_replay':
        events=[dict(id='a',kind='issue',token='old',ts=0,expires=30,subject='alice',groups=['engineering']),
          dict(id='b',kind='refresh',token='new',parent='old',ts=2,expires=50),
          dict(id='c',kind='issue',token='bob',ts=1,expires=40,subject='bob',groups=['contractor']),
          dict(id='d',kind='revoke',token='bob',ts=3),
          dict(id='e',kind='issue',token='expired',ts=0,expires=4,subject='eve',groups=['engineering']),
          dict(id='f',kind='refresh',token='too_late',parent='expired',ts=5,expires=30),
          dict(id='g',kind='revoke',token='pre_revoked',ts=0),
          dict(id='h',kind='issue',token='pre_revoked',ts=1,expires=30,subject='eve',groups=['contractor']),
          dict(id='i',kind='issue',token='service',ts=4,expires=40,subject='svc',groups=['service']),
          dict(id='j',kind='issue',token='future',ts=70,expires=90,subject='future',groups=[])]
        if seed%3==0: events.append(dict(id='k',kind='revoke',token='old',ts=8))
        rng.shuffle(events); return dict(now=10,events=events)
    if op=='federation_authorize':
        groups=[dict(id='engineering',parents=['staff'],roles=['developer']),dict(id='staff',parents=['engineering'],roles=['reader']),dict(id='contractor',parents=['staff'],roles=['restricted']),dict(id='service',parents=[],roles=['automation'])]
        rules=[dict(id='read',role='reader',resource='repo/*',action='read',effect='allow'),dict(id='write',role='developer',resource='repo/*',action='write',effect='allow'),dict(id='restrict',role='restricted',resource='repo/private*',action='*',effect='deny'),dict(id='auto',role='automation',resource='jobs/*',action='run',effect='allow')]
        return dict(groups=groups,rules=rules,requests=[dict(id='r0',token='new',resource='repo/private',action='read'),dict(id='r1',token='bob',resource='repo/private',action='read'),dict(id='r2',token='service',resource='jobs/reindex',action='run'),dict(id='r3',token='old',resource='repo/x',action='read'),dict(id='r4',token='missing',resource='repo/x',action='read')])
    if op=='schema_migration':
        return dict(old=[dict(name='legacy_id',type='int',required=True),dict(name='title',type='str',required=False)],
          new=[dict(name='doc_id',type='float',required=True),dict(name='title',type='str',required=True,default=''),dict(name='region',type='str',required=True,default='global')],
          renames=[{'from':'legacy_id','to':'intermediate'},{'from':'intermediate','to':'doc_id'}])
    if op=='shard_replay':
        replicas=[]; events=[]
        for i in range(3):
            for j in range(3):
                ident=f'p{i}-r{j}'; replicas.append(dict(id=ident,shard=f'p{i}',host=f'h{j}',checkpoint=-1,documents=[]))
                entries=[dict(replica=ident,offset=0,epoch=1,op='upsert',id='alive',version=1,fields={'value':i+shift}),
                  dict(replica=ident,offset=1,epoch=1,op='upsert',id='gone',version=1,fields={'value':9}),
                  dict(replica=ident,offset=2,epoch=1,op='delete',id='gone',version=2),
                  dict(replica=ident,offset=3,epoch=1,op='upsert',id='gone',version=1,fields={'value':9})]
                if j==2 and i==2: entries=[r for r in entries if r['offset']!=2]  # Gap leaves stale material.
                events+=entries
        events+=copy.deepcopy(events[:2]); rng.shuffle(events); return dict(replicas=replicas,events=events)
    if op=='quorum_cutover':
        partitions=[dict(id=f'p{i}',quorum=2,value=5+(i*3+seed)%7,target_sha256=canonical([dict(id='alive',version=1,fields={'value':i+shift})]),target_offset=3) for i in range(3)]
        return dict(partitions=partitions,candidates=[dict(id=f'c{i}{j}',replica=f'p{i}-r{j}',cost=1+(i+j+seed)%4) for i in range(3) for j in range(3)],budget=10+seed%3)
    if op=='trust_paths':
        nodes=[dict(id='rootA',expires=500,revoked=False),dict(id='rootB',expires=600,revoked=False),dict(id='caA',expires=150,revoked=False),dict(id='caB',expires=500,revoked=False)]
        nodes += [dict(id=f'cert{i}',expires=400+i*3,revoked=i==5) for i in range(6)]
        edges=[dict(issuer='rootA',subject='caA',expires=500),dict(issuer='rootB',subject='caB',expires=500),dict(issuer='caA',subject='caB',expires=120),dict(issuer='caB',subject='caA',expires=300)]
        for i in range(6):
            edges.extend([dict(issuer='caA',subject=f'cert{i}',expires=400),dict(issuer='caB',subject=f'cert{i}',expires=450)])
        return dict(now=50+shift,nodes=nodes,roots=['rootA','rootB'],edges=edges)
    if op=='certificate_policy':
        return dict(rules=[dict(id='rotate',resource='cert*',action='rotate',priority=1,effect='allow'),dict(id='deny5',resource='cert5',action='rotate',priority=2,effect='deny')],requests=[dict(resource=f'cert{i}',action='rotate') for i in range(6)])
    if op=='recovery_chain':
        state=[dict(key='b',value=5),dict(key='k',value=3+shift)]
        return dict(target=9,snapshots=[
          dict(id='base',kind='full',parent=None,start=0,end=2,cost=2,epoch=1,valid=True,state=[dict(key='k',value=1)]),
          dict(id='inc',kind='incremental',parent='base',start=2,end=4,cost=3,epoch=1,valid=True,state=state),
          dict(id='expensive',kind='full',parent=None,start=0,end=4,cost=12,epoch=1,valid=True,state=state),
          dict(id='broken',kind='incremental',parent='inc',start=5,end=7,cost=1,epoch=1,valid=True,state=[]),
          dict(id='wrong_epoch',kind='incremental',parent='inc',start=4,end=8,cost=1,epoch=2,valid=True,state=[]),
          dict(id='invalid',kind='incremental',parent='inc',start=4,end=9,cost=1,epoch=1,valid=False,state=[])])
    if op=='transaction_replay':
        records=[]
        def row(lsn,tx,kind,**kw): records.append(dict(lsn=lsn,epoch=1,tx=tx,kind=kind,**kw))
        row(0,'old','write',seq=0,key='k',value=1); row(1,'old','commit',count=1)
        row(2,'included','write',seq=0,key='k',value=3+shift); row(3,'included','write',seq=1,key='b',value=5); row(4,'included','commit',count=2)
        row(5,'atomic','write',seq=0,key='k',value=7+shift); row(6,'atomic','write',seq=1,key='k',value=8+shift); row(7,'atomic','commit',count=2)
        row(8,'aborted','write',seq=0,key='ghost',value=99); row(9,'aborted','abort'); row(10,'pending','write',seq=0,key='ghost',value=100)
        records+=copy.deepcopy(records[:2]); rng.shuffle(records); return dict(checkpoint=-1,records=records)
    if op=='restore_join': return dict(target=9,rto=12,expected_sha256=canonical([dict(key='b',value=5),dict(key='k',value=8+shift)]))
    if op=='retention_optimizer':
        return dict(archives=[dict(id=f'a{i}',category=['hot','cold'][i%2],hold=i in (0,3),modes=[dict(id='full',bytes=4,value=9+(i+seed)%5),dict(id='compressed',bytes=2,value=3+(i*3+seed)%5)]) for i in range(7)],budget=15,minimums={'hot':2,'cold':2})
    if op=='retention_audit_logs': return dict(lines=[f'INFO request=q{i} archive=a{i} token="secret {i}"' for i in range(6)])
    if op=='retention_audit':
        return dict(rules=[dict(id='read',resource='archive/*',action='read',priority=1,effect='allow')],requests=[dict(id=f'q{i}',archive=f'a{i}',resource=f'archive/a{i}',action='read') for i in range(7)])
    if op=='ecmp_routes':
        return dict(nodes=['a','b','c','d','isolated'],edges=[{'from':a,'to':b,'weight':w} for a,b,w in [('a','b',1),('a','c',1),('b','d',1),('c','d',1),('a','d',4),('d','a',3)]],sources=['a','d'],targets=['a','d'],failed_nodes=[],failed_edges=[])
    if op=='stateful_acl':
        rules=[dict(id='open',src='a',dst='d',protocol='tcp',priority=1,effect='allow'),dict(id='reverse-deny',src='d',dst='a',protocol='*',priority=5,effect='deny')]
        events=[]
        for i,(ts,src,dst,sport,dport,flag,protocol) in enumerate([(0,'a','d',1000,443,'syn','tcp'),(1,'d','a',443,1000,'data','tcp'),(2,'a','d',1000,443,'fin','tcp'),(3,'d','a',443,1000,'data','tcp'),(10,'a','d',1000,443,'syn','tcp'),(15,'a','d',1000,443,'data','tcp'),(16,'a','d',2000,443,'syn','udp')]):
            events.append(dict(id=f'e{i}',ts=ts,seq=0,src=src,dst=dst,sport=sport,dport=dport,flag=flag,protocol=protocol))
        rng.shuffle(events); return dict(timeout=5,rules=rules,events=events)
    if op=='network_join':
        return dict(probes=[dict(id=f'p{i}',event=f'e{i}',source='d' if i in (1,3) else 'a',target='a' if i in (1,3) else 'd',hops=['d','a'] if i in (1,3) else ['a','d'] if i==4 else ['a','b','d'] if i%2==0 else ['a','c','d']) for i in range(6)])
    raise ValueError(op)

def enhanced_specs(suite,index):
    seed=100+index*17; specs=[]; inputs={}
    def add(name,op,deps=(),fixture_op=None,raw=None):
        from build import contract
        rel=f'inputs/{name}.json'; inputs[rel]=copy.deepcopy(raw) if raw is not None else new_fixture(fixture_op or op,seed)
        folder=f'engines/{name}' if suite=='reasoning4' else f'products/{name}' if suite=='linux2' else name
        c=contract(name,op,[rel]+list(deps),seed+len(specs)); specs.append(dict(folder=folder,contract=c)); return c['output']
    if index==7:
        from specification import fixture
        a=add('notice_windows','notice_coverage'); b=add('support_assignment','capacity_assignment',raw=fixture('capacity_assignment',seed))
        add('retirement_order','resource_cutover',[a,b])
    elif index==9:
        schema=dict(old=[dict(name='subject',type='str',required=True)],new=[dict(name='subject',type='str',required=True),dict(name='tenant',type='str',required=True,default='default')])
        a=add('claims','schema_compatibility',raw=schema); b=add('sessions','session_replay'); add('authorization','federation_authorize',[a,b])
    elif index==11:
        a=add('mapping_compat','schema_migration'); b=add('shard_replay','shard_replay'); add('cutover_plan','quorum_cutover',[a,b])
    elif index==12:
        a=add('trust_graph','trust_paths'); b=add('trust_policy','policy_precedence',fixture_op='certificate_policy'); add('renewal_windows','certificate_schedule',[a,b])
    elif index==13:
        a=add('backup_graph','recovery_chain'); b=add('journal_restore','transaction_replay'); add('backup_windows','restore_join',[a,b])
    elif index==14:
        a=add('archive_logs','log_compatibility',fixture_op='retention_audit_logs'); b=add('retention_windows','retention_optimizer'); add('retention_policy','retention_audit',[a,b])
    elif index==15:
        a=add('route_graph','ecmp_routes'); b=add('firewall_policy','stateful_acl'); add('network_traces','network_join',[a,b])
    else: return None
    return specs,inputs

def new_vectors(spec,s,original):
    """Held-out raw and dependency mutations. Expected values never reach candidate code."""
    c=s['contract']; op=c['operation']; cases=[]
    def add(payloads,contract=None): cases.append(dict(payloads=copy.deepcopy(payloads),contract=copy.deepcopy(contract or c)))
    add(original)
    for seed in (701+spec['index']*3,902+spec['index']*5): add([new_fixture(op,seed)]+original[1:])
    from specification import empty
    add([empty(op)]+original[1:]); add([{}]+original[1:])
    bad=copy.deepcopy(original); bad[0]['unused_field']={'nonfinite':float('nan')}; add(bad)
    if len(original)>1: add(original[:1])  # Missing producer must be an error, never silently optional.
    p=copy.deepcopy(original[0]); extra=copy.deepcopy(original[1:])
    if op=='notice_coverage':
        trap=dict(clients=[dict(id=n,weight=v,deadline=10,mandatory=False) for n,v in [('a',10),('b',6),('c',6)]],windows=[dict(id='large',start=0,end=4,cost=4,clients=['a']),dict(id='left',start=0,end=2,cost=2,clients=['b']),dict(id='right',start=2,end=4,cost=2,clients=['c'])],budget=4,cooldown=0)
        add([trap]); p['budget']=0; add([p]); p=copy.deepcopy(original[0]); p['windows'].append(copy.deepcopy(p['windows'][0])); add([p])
        p=copy.deepcopy(original[0]); p['clients'][0]['deadline']=0; add([p])
    elif op=='resource_cutover':
        x=copy.deepcopy(original); x[1]['result']['completion']={k:100 for k in x[1]['result']['completion']}; add(x)
        x=copy.deepcopy(original); x[2]['result']['feasible']=False; add(x)
        x=copy.deepcopy(original); x[0]['capacity']=1; add(x)
        x=copy.deepcopy(original); x[0]['nodes'][0]['deps']=['j5']; x[0]['nodes'][5]['deps']=['j0']; add(x)
    elif op=='session_replay':
        add([dict(now=10,events=[dict(id='i',kind='issue',token='root',ts=0,expires=2,subject='u',groups=[]),dict(id='f',kind='refresh',token='child',parent='root',ts=1,expires=30)])])
        p['events'].append(dict(id='late-revoke',kind='revoke',token='old',ts=9)); add([p])
        p=copy.deepcopy(original[0]); p['events'].append(dict(id='duplicate-token',kind='issue',token='old',ts=6,expires=60,subject='x',groups=[])); add([p])
        p=copy.deepcopy(original[0]); p['now']=True; add([p])
    elif op=='federation_authorize':
        x=copy.deepcopy(original); x[1]['result']['compatible']=False; add(x)
        x=copy.deepcopy(original); x[2]['result']['active_tokens']=[]; add(x)
        x=copy.deepcopy(original); x[0]['rules'].append(dict(id='deny',role='reader',resource='repo/*',action='read',effect='deny')); add(x)
        x=copy.deepcopy(original); x[0]['groups'][0]['parents'].append('missing'); add(x)
    elif op=='schema_migration':
        p['renames'] += [{'from':'unused_a','to':'unused_b'},{'from':'unused_b','to':'unused_a'}]; add([p])
        p=copy.deepcopy(original[0]); p['renames'].append({'from':'title','to':'doc_id'}); add([p])
        p=copy.deepcopy(original[0]); p['new'][0]['type']='str'; add([p])
        p=copy.deepcopy(original[0]); p['new'][1].pop('default',None); add([p])
    elif op=='shard_replay':
        p['events']=[e for e in p['events'] if e['offset']!=1]; add([p])
        p=copy.deepcopy(original[0]); e=copy.deepcopy(p['events'][0]); e['version']+=1; p['events'].append(e); add([p])
        p=copy.deepcopy(original[0]); p['events'][0]['offset']=True; add([p])
        p=copy.deepcopy(original[0]); p['events'].append(dict(replica='p0-r0',offset=4,epoch=1,op='upsert',id='gone',version=2,fields={'value':1})); add([p])
    elif op=='quorum_cutover':
        x=copy.deepcopy(original); x[1]['result']['compatible']=False; add(x)
        x=copy.deepcopy(original)
        for rep in x[2]['result']['replicas']: rep['host']='same-host'
        add(x)
        x=copy.deepcopy(original); x[2]['result']['replicas'][0]['sha256']='0'*64; add(x)
        x=copy.deepcopy(original); x[0]['budget']=0; add(x)
        data,replay=quorum_trap(); add([data,{'name':'schema','result':{'compatible':True}},{'name':'replay','result':replay}])
    elif op=='trust_paths':
        p['nodes'][3]['revoked']=True; add([p]); p=copy.deepcopy(original[0]); p['roots']=[]; add([p])
        p=copy.deepcopy(original[0]); p['nodes'][0]['expires']=0; add([p]); p=copy.deepcopy(original[0]); p['edges'].append(copy.deepcopy(p['edges'][0])); add([p])
    elif op=='certificate_schedule':
        x=copy.deepcopy(original); x[1]['result']['trusted']=[r for r in x[1]['result']['trusted'] if r['id']!='cert0']; add(x)
        x=copy.deepcopy(original)
        for d in x[2]['result']['decisions']:
            if d['resource']=='cert0': d['effect']='deny'
        add(x)
        x=copy.deepcopy(original); x[0]['budget']=0; add(x)
    elif op=='recovery_chain':
        for r in p['snapshots']: r['valid']=False
        add([p]); p=copy.deepcopy(original[0]); p['snapshots'][0]['parent']='inc'; add([p])
        p=copy.deepcopy(original[0]); p['target']=2; add([p]); p=copy.deepcopy(original[0]); p['snapshots'][0]['cost']=-1; add([p])
    elif op=='transaction_replay':
        p['records']=[r for r in p['records'] if r['lsn']!=3]; add([p])
        p=copy.deepcopy(original[0])
        for r in p['records']:
            if r['lsn']==6: r['seq']=3
        add([p]); p=copy.deepcopy(original[0]); r=copy.deepcopy(p['records'][0]); r['tx']='conflict'; p['records'].append(r); add([p])
        p=copy.deepcopy(original[0]); p['records'].append(dict(lsn=11,epoch=1,tx='atomic',kind='abort')); add([p])
    elif op=='restore_join':
        x=copy.deepcopy(original); x[1]['result']['feasible']=False; add(x)
        x=copy.deepcopy(original); x[2]['result']['watermark']=x[0]['target']-1; add(x)
        x=copy.deepcopy(original); x[0]['rto']=0; add(x)
        x=copy.deepcopy(original); x[0]['expected_sha256']='0'*64; add(x)
        x=copy.deepcopy(original); x[2]['result']['incomplete_commits']=[dict(tx='missing-write',commit_lsn=x[0]['target'])]; add(x)
    elif op=='retention_optimizer':
        p['archives'][0]['modes']=[]; add([p]); p=copy.deepcopy(original[0]); p['budget']=0; add([p])
        trap=dict(archives=[dict(id='a',category='x',hold=False,modes=[dict(id='full',bytes=3,value=5)]),dict(id='b',category='x',hold=False,modes=[dict(id='full',bytes=2,value=3)]),dict(id='c',category='x',hold=False,modes=[dict(id='full',bytes=2,value=3)])],budget=4,minimums={})
        add([trap]); p=copy.deepcopy(original[0]); p['archives'][0]['hold']=1; add([p])
    elif op=='retention_audit':
        x=copy.deepcopy(original); x[1]['result']['lines']=[]; add(x)
        x=copy.deepcopy(original); x[2]['result']['selected']=[]; add(x)
        x=copy.deepcopy(original); x[1]['result']['lines'].append(x[1]['result']['lines'][0]); add(x)
        x=copy.deepcopy(original); x[2]['result']['feasible']=False; add(x)
    elif op=='ecmp_routes':
        p['failed_edges']=[['b','d']]; add([p]); p=copy.deepcopy(original[0]); p['failed_nodes']=['c']; add([p])
        p=copy.deepcopy(original[0]); p['edges'].append(copy.deepcopy(p['edges'][0])); add([p])
        p=copy.deepcopy(original[0]); p['edges'][0]['weight']=0; add([p])
    elif op=='stateful_acl':
        p['timeout']=2; add([p]); p=copy.deepcopy(original[0]); p['rules']=[]; add([p])
        p=copy.deepcopy(original[0]); p['events'].append(copy.deepcopy(p['events'][0])); add([p]); p=copy.deepcopy(original[0]); p['events'][0]['sport']=0; add([p])
    elif op=='network_join':
        x=copy.deepcopy(original); x[1]['result']['active_edges']=[r for r in x[1]['result']['active_edges'] if (r['from'],r['to'])!=('a','b')]; add(x)
        x=copy.deepcopy(original)
        for d in x[2]['result']['decisions']: d['allowed']=False
        add(x)
        x=copy.deepcopy(original); x[0]['probes'][0]['event']='missing'; add(x)
        x=copy.deepcopy(original); x[1]['result']['routes']=[]; add(x)
    return cases

def quorum_trap():
    digest=canonical([]); replicas=[]; candidates=[]
    for i in range(3):
        for j in range(2):
            replicas.append(dict(id=f'r{i}{j}',shard=f'p{i}',host=f'h{j}',applied_offset=0,sha256=digest))
            candidates.append(dict(id=f'c{i}{j}',replica=f'r{i}{j}',cost=2 if i==0 else 1))
    parts=[dict(id=f'p{i}',quorum=2,value=9 if i==0 else 5,target_offset=0,target_sha256=digest) for i in range(3)]
    return dict(partitions=parts,candidates=candidates,budget=4),dict(replicas=replicas)

def independent_audit():
    """Small exact counterexamples + independent enumeration/Floyd checks."""
    audits=0
    trap=dict(clients=[dict(id=n,weight=v,deadline=10,mandatory=False) for n,v in [('a',10),('b',6),('c',6)]],windows=[dict(id='large',start=0,end=4,cost=4,clients=['a']),dict(id='left',start=0,end=2,cost=2,clients=['b']),dict(id='right',start=2,end=4,cost=2,clients=['c'])],budget=4,cooldown=0)
    assert coverage(trap)['selected']==['left','right']; audits+=1
    # Independently enumerate every integer start vector, rather than priority-list schedules.
    for seed in range(8):
        rng=random.Random(seed); nodes=[dict(id=f'j{i}',client=f'j{i}',duration=rng.randint(1,2),demand=rng.randint(1,2),deps=['j0'] if i==2 else []) for i in range(3)]
        p=dict(nodes=nodes,capacity=2,horizon=9); completion={f'j{i}':rng.randint(0,2) for i in range(3)}
        notice=dict(feasible=True,completion=completion); staff=dict(feasible=True,assignments=[dict(job=f'j{i}',worker=f'w{i%2}') for i in range(3)])
        candidates=[]
        for starts in itertools.product(range(9),repeat=3):
            ends=[s+r['duration'] for s,r in zip(starts,nodes)]
            if any(starts[i]<completion[r['client']] or ends[i]>9 for i,r in enumerate(nodes)): continue
            if starts[2]<ends[0]: continue
            if not (ends[0]<=starts[2] or ends[2]<=starts[0]): continue
            if any(sum(r['demand'] for i,r in enumerate(nodes) if starts[i]<=t<ends[i])>2 for t in range(9)): continue
            candidates.append((max(ends),sum(starts),starts))
        expected=min(candidates) if candidates else None; got=resource_schedule(p,notice,staff)
        assert (got['makespan'],got['total_start'],tuple(r['start'] for r in got['schedule']))==expected
        audits+=1
    basic=dict(now=10,events=[dict(id='a',kind='issue',token='old',subject='u',groups=[],ts=0,expires=2),dict(id='b',kind='refresh',token='new',parent='old',ts=1,expires=30)])
    assert [r['token'] for r in sessions(basic)['active_tokens']]==['new']; audits+=1
    basic['events'].append(dict(id='c',kind='revoke',token='old',ts=3)); assert not sessions(basic)['active_tokens']; audits+=1
    auth=new_fixture('federation_authorize',1); state=dict(active_tokens=[dict(token='bob',subject='b',groups=['contractor'],expires=50)])
    decision=authorize(auth,dict(compatible=True),state)['decisions'][1]
    assert decision['effect']=='deny' and decision['rule_id']=='restrict' and decision['roles']==['developer','reader','restricted']; audits+=1
    assert schema_migration(new_fixture('schema_migration',1))['field_map']['legacy_id']=='doc_id'; audits+=1
    r=replay_shards(new_fixture('shard_replay',1))
    assert r['replicas'][0]['tombstones']=={'gone':2} and [d['id'] for d in r['replicas'][0]['documents']]==['alive']; audits+=1
    p,r=quorum_trap(); got=quorum(p,dict(compatible=True),r)
    assert got['partitions']==['p1','p2'] and got['value']==10 and got['cost']==4; audits+=1
    # Enumerate simple trust paths independently of the widest-path algorithm.
    for removed in (None,'caB'):
        p=new_fixture('trust_paths',1)
        if removed:
            next(r for r in p['nodes'] if r['id']==removed)['revoked']=True
        nodes={r['id']:r for r in p['nodes']}; paths=defaultdict(list)
        def walk(path,expiry):
            a=path[-1]; r=nodes[a]
            if r['revoked'] or r['expires']<=p['now']: return
            expiry=min(expiry,r['expires']); paths[a].append((expiry,path[:]))
            for e in p['edges']:
                if e['issuer']==a and e['subject'] not in path and e['expires']>p['now']: walk(path+[e['subject']],min(expiry,e['expires']))
        for root in p['roots']: walk([root],math.inf)
        expected={n:min(choices,key=lambda t:(-t[0],len(t[1]),t[1])) for n,choices in paths.items()}
        actual=trust(p)
        assert {r['id']:(r['valid_until'],r['path']) for r in actual['trusted']}==expected; audits+=1
    cp=new_fixture('certificate_schedule',1); paths=trust(new_fixture('trust_paths',1)); decisions=policy(new_fixture('certificate_policy',1))
    assert certificate_schedule(cp,paths,decisions)['feasible']
    for d in decisions['decisions']:
        if d['resource']=='cert0': d['effect']='deny'
    assert not certificate_schedule(cp,paths,decisions)['feasible']; audits+=1
    base=recovery(new_fixture('recovery_chain',1)); log=transactions(new_fixture('transaction_replay',1))
    assert base['chain']==['base','inc'] and base['cost']==5 and base['snapshot_end']==4; audits+=1
    assert [r['tx'] for r in log['transactions']]==['old','included','atomic'] and log['incomplete']==['pending']; audits+=1
    restored=restore(new_fixture('restore_join',1),base,log)
    assert restored['feasible'] and restored['applied']==['atomic'] and restored['state']==[dict(key='b',value=5),dict(key='k',value=9)]; audits+=1
    trap=dict(archives=[dict(id='a',category='x',hold=False,modes=[dict(id='m',bytes=3,value=5)]),dict(id='b',category='x',hold=False,modes=[dict(id='m',bytes=2,value=3)]),dict(id='c',category='x',hold=False,modes=[dict(id='m',bytes=2,value=3)])],budget=4,minimums={})
    assert retention(trap)['selected']==[dict(archive='b',mode='m'),dict(archive='c',mode='m')]; audits+=1
    for failed in ([],[['b','d']]):
        p=new_fixture('ecmp_routes',1); p['failed_edges']=failed; got=routes(p); ids=p['nodes']; distances={(a,b):0 if a==b else math.inf for a in ids for b in ids}
        for e in p['edges']:
            if [e['from'],e['to']] not in failed: distances[e['from'],e['to']]=e['weight']
        for middle in ids:
            for a in ids:
                for b in ids: distances[a,b]=min(distances[a,b],distances[a,middle]+distances[middle,b])
        for r in got['routes']:
            d=distances[r['source'],r['target']]
            expected=sorted(e['to'] for e in p['edges'] if e['from']==r['source'] and [e['from'],e['to']] not in failed and e['weight']+distances[e['to'],r['target']]==d) if d not in (0,math.inf) else []
            assert r['distance']==(None if d==math.inf else d) and r['next_hops']==expected
        audits+=1
    firewall=acl(new_fixture('stateful_acl',1)); assert [d['allowed'] for d in firewall['decisions']]==[True,True,True,False,True,False,False]; audits+=1
    assert network(new_fixture('network_join',1),routes(new_fixture('ecmp_routes',1)),firewall)['reachable_count']==3; audits+=1
    return audits

def duplicate_audit(root,specs):
    """Exact duplicates and name-independent algorithm/dependency fingerprints."""
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8')); byentry={e['entry_id']:e for e in manifest['entries']}
    groups={k:defaultdict(list) for k in ('prompt','workspace','algorithm_dependencies','complete_input_bundle','component_input')}; entries=[]
    for key,spec in specs.items():
        e=byentry[key]; owners={s['contract']['output']:s['contract']['operation'] for s in spec['specs']}
        if any('outputs/domain_core.json' in s['contract']['inputs'] for s in spec['specs']): owners['outputs/domain_core.json']='<domain_core>'
        graph=[]; inputs=[]
        for s in spec['specs']:
            c=s['contract']; graph.append(dict(operation=c['operation'],upstream=sorted(owners[p] for p in c['inputs'] if p in owners)))
            for p in c['inputs']:
                if p in spec['inputs']:
                    h=canonical(spec['inputs'][p]); groups['component_input'][h].append(key+':'+c['name']); inputs.append((c['operation'],h))
        if '<domain_core>' in owners.values(): graph.append(dict(operation='<domain_core>',upstream=sorted(s['contract']['operation'] for s in spec['specs'] if s['folder'].startswith('domains/'))))
        graph.sort(key=lambda r:json.dumps(r,sort_keys=True)); gh=canonical(graph); ih=canonical(sorted(inputs))
        groups['prompt'][e['task_prompt_sha256']].append(key); groups['workspace'][e['workspace_tree_sha256']].append(key); groups['algorithm_dependencies'][gh].append(key); groups['complete_input_bundle'][ih].append(key)
        entries.append(dict(entry=key,algorithm_dependency_sha256=gh,input_bundle_sha256=ih))
    duplicates={kind:[members for members in mapping.values() if len(members)>1] for kind,mapping in groups.items()}
    assert all(not duplicates[k] for k in ('prompt','workspace','algorithm_dependencies','complete_input_bundle')),'task-level duplicates detected'
    return dict(entry_count=len(entries),task_level_duplicates=False,duplicate_groups=duplicates,entries=entries,
        method='Compare prompt/workspace hashes, full input bundles, and name-independent operation/dependency graphs. This detects template-level repetition, not formal program equivalence. Shared component fixtures/algorithms do not imply duplicate whole tasks.')

def algorithm_mutant(payloads,c):
    """Plausible but incorrect implementations used exclusively for rejection tests."""
    from reference import evaluate
    p=copy.deepcopy(unwrap(payloads[0])); op=c['operation']
    if op=='session_replay':
        ancestors={e['parent'] for e in p['events'] if e['kind']=='refresh'}
        p['events']=[e for e in p['events'] if not(e['kind']=='revoke' and e['token'] in ancestors)]
        return dict(name=c['name'],result=sessions(p))
    result=evaluate(payloads,c)
    if op=='notice_coverage':
        # Incorrectly choose a single highest-value window, ignoring combinations.
        choices=[]
        for w in p['windows']:
            candidate=copy.deepcopy(p); candidate['windows']=[w]; choices.append(coverage(candidate))
        good=[r for r in choices if r['feasible']]
        result['result']=min(good,key=lambda r:(-r['value'],r['cost'],r['selected'])) if good else dict(feasible=False,selected=[],value=0,cost=0,completion={})
    elif op=='schema_migration':
        # Incorrectly apply only a single rename edge instead of transitive closure.
        direct={r['from']:r['to'] for r in p['renames']}
        old=[dict(r,name=direct.get(r['name'],r['name'])) for r in p['old']]
        result['result']=dict(**compatibility(dict(old=old,new=p['new'])),field_map={r['name']:direct.get(r['name'],r['name']) for r in p['old']})
    elif op=='trust_paths':
        nodes={r['id']:r for r in p['nodes']}; adjacency=defaultdict(list)
        for e in p['edges']: adjacency[e['issuer']].append(e)
        seen={}; heap=[]
        for root in p['roots']:
            if not nodes[root]['revoked'] and nodes[root]['expires']>p['now']: heapq.heappush(heap,(0,(root,),nodes[root]['expires']))
        while heap:
            n,path,expiry=heapq.heappop(heap); a=path[-1]
            if a in seen: continue
            seen[a]=dict(id=a,path=list(path),valid_until=expiry)
            for e in adjacency[a]:
                b=e['subject']; bottleneck=min(expiry,e['expires'],nodes[b]['expires'])
                if not nodes[b]['revoked'] and bottleneck>p['now'] and b not in seen: heapq.heappush(heap,(n+1,path+(b,),bottleneck))
        result['result']=dict(trusted=[seen[n] for n in sorted(seen)],untrusted=sorted(set(nodes)-set(seen)))
    elif op=='transaction_replay':
        # Incorrectly expose uncommitted transaction writes as completed transactions.
        writes=defaultdict(list)
        for r in p['records']:
            if r['kind']=='write' and r['lsn']<=result['result']['watermark']: writes[r['tx']].append(r)
        committed={r['tx'] for r in result['result']['transactions']}
        for tx,rows in writes.items():
            if tx not in committed:
                result['result']['transactions'].append(dict(tx=tx,commit_lsn=max(r['lsn'] for r in rows),writes=[dict(key=r['key'],value=r['value']) for r in rows],duration=len(rows)))
        result['result']['transactions'].sort(key=lambda r:(r['commit_lsn'],r['tx']))
    elif op=='retention_optimizer':
        # Incorrectly take each archive's full/highest-value mode before considering others.
        selected=[]; size=0; value=0
        for archive in sorted(p['archives'],key=lambda r:(not r['hold'],-max((m['value'] for m in r['modes']),default=0),r['id'])):
            for mode in sorted(archive['modes'],key=lambda m:(-m['value'],m['bytes'],m['id'])):
                if size+mode['bytes']<=p['budget']:
                    size+=mode['bytes']; value+=mode['value']; selected.append(dict(archive=archive['id'],mode=mode['id'])); break
        result['result']=dict(feasible=True,selected=sorted(selected,key=lambda r:(r['archive'],r['mode'])),bytes=size,value=value)
    elif op=='ecmp_routes':
        for route in result['result']['routes']: route['next_hops']=route['next_hops'][:1]
    return result
