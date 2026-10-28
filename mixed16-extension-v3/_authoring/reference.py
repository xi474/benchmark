"""Author-only reference algorithms. Never mount this directory in an agent workspace."""
from __future__ import annotations
import copy
import fnmatch
import hashlib
import json
import math
import re
from bisect import bisect_right
from collections import Counter, defaultdict, deque

def integer(x, minimum=None):
    if type(x) is not int or (minimum is not None and x < minimum):
        raise ValueError('invalid integer')
    return x

def number(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError('invalid finite number')
    return x

def text(x):
    if not isinstance(x, str) or not x.strip():
        raise ValueError('empty or invalid text')
    return x.strip()

def array(x):
    if not isinstance(x, list): raise ValueError('expected array')
    return x

def obj(x):
    if not isinstance(x, dict): raise ValueError('expected object')
    return x

def distinct(rows):
    ids = [text(obj(r)['id']) for r in rows]
    if len(set(ids)) != len(ids): raise ValueError('duplicate id')

def unwrap(p):
    return p['result'] if isinstance(p, dict) and set(p) == {'name', 'result'} else p

def records_from(payloads):
    rows = {}
    for p in payloads:
        for r in obj(unwrap(p))['records']:
            k = (r['source'], r['id'])
            if k in rows and rows[k] != r: raise ValueError('conflicting source/id')
            rows[k] = copy.deepcopy(r)
    return sorted(rows.values(), key=lambda r:(r['source'], r['id']))

def evidence(p, c):
    revisions = {}
    for raw in array(p):
        r = obj(raw)
        ident = text(r['id']); rev = integer(r['revision'], 0)
        owner = text(r['owner']).lower(); tags = sorted(set(text(t).lower() for t in array(r['tags'])))
        category = text(r['category']).lower()
        if category not in ('prepare','copy','verify'): raise ValueError('invalid category')
        failures = integer(r['failures'], 0); total = integer(r['total'], 1)
        lag = integer(r['lag'], 0); valid = r['valid']
        if type(valid) is not bool or failures > total: raise ValueError('invalid evidence')
        norm = dict(id=ident, revision=rev, owner=owner, tags=tags, category=category,
                    failures=failures,total=total,lag=lag,valid=valid)
        key=(ident,rev)
        if key in revisions and revisions[key] != norm: raise ValueError('revision conflict')
        revisions[key]=norm
    latest={}
    for (ident, rev),r in revisions.items():
        if ident not in latest or rev>latest[ident]['revision']: latest[ident]=r
    rows=[]
    for r in latest.values():
        mode=c['operation']
        if mode=='failure_evidence': score=(20*r['failures']+r['total']-1)//r['total']
        elif mode=='lag_evidence': score=(r['lag']+c['sla']-1)//c['sla']
        else: score=(0 if r['valid'] else 15)+r['failures']
        score=max(0,min(20,score+c['offset']))
        rows.append(dict(id=r['id'],source=c['name'],owner=r['owner'],tags=r['tags'],category=r['category'],score=score))
    rows.sort(key=lambda r:(r['source'],r['id']))
    return dict(records=rows,count=len(rows),score_total=sum(r['score'] for r in rows))

def ranking(payloads,c):
    rows=records_from(payloads)
    selected=[r for r in rows if r['score']>=c['threshold']]
    selected.sort(key=lambda r:(-r['score'],r['source'],r['id']))
    selected=selected[:c['limit']]
    return dict(records=sorted(selected,key=lambda r:(r['source'],r['id'])),
                ranking=[r['source']+':'+r['id'] for r in selected],score_total=sum(r['score'] for r in selected))

def balancing(payloads,c):
    rows=records_from(payloads); loads={w:0 for w in c['reviewers']}; assignments=[]
    for r in sorted(rows,key=lambda r:(-r['score'],r['source'],r['id'])):
        w=min(loads,key=lambda w:(loads[w],w))
        loads[w]+=r['score']; assignments.append(dict(id=r['source']+':'+r['id'],reviewer=w))
    return dict(records=rows,assignments=sorted(assignments,key=lambda r:r['id']),loads=loads)

def dependency_plan(payloads,c):
    rows=records_from(payloads)
    if c.get('only_if_blocking') and not any('blocking' in r['tags'] and r['score']>=c['threshold'] for r in rows):
        rows=[]
    order={'prepare':0,'copy':1,'verify':2}
    nodes=[]
    for r in rows:
        rank=order[r['category']]
        deps=[v['source']+':'+v['id'] for v in rows if order[v['category']]<rank]
        nodes.append(dict(id=r['source']+':'+r['id'],duration=1+r['score']//5,deps=deps))
    return dict(records=rows,**dag({'nodes':nodes}))

def weighted(p,c):
    rows=array(obj(p)['windows']); distinct(rows)
    cooldown=integer(c['cooldown'],0)
    jobs=[]
    for r in rows:
        start=integer(r['start'],0); end=integer(r['end'],0); value=integer(r['value'])
        if end<=start: raise ValueError('invalid interval')
        jobs.append(dict(id=text(r['id']),start=start,end=end,value=value))
    def compatible(a,b): return a['end']+cooldown<=b['start'] or b['end']+cooldown<=a['start']
    def optimum(forced,excluded):
        if any(not compatible(a,b) for i,a in enumerate(forced) for b in forced[i+1:]): return None
        fixed={r['id'] for r in forced}
        free=sorted((r for r in jobs if r['id'] not in fixed|excluded and all(compatible(r,f) for f in forced)),key=lambda r:(r['end'],r['start'],r['id']))
        ends=[r['end'] for r in free]; best=[0]
        for i,r in enumerate(free):
            prev=bisect_right(ends,r['start']-cooldown,0,i)
            best.append(max(best[-1],best[prev]+r['value']))
        return sum(r['value'] for r in forced)+best[-1]
    target=optimum([],set()); forced=[]; excluded=set()
    # Lexicographic order on variable-length ID lists needs feasibility-guided recovery.
    # A naive local tie-break in DP is incorrect when zero-valued windows exist.
    for r in sorted(jobs,key=lambda r:r['id']):
        if sum(f['value'] for f in forced)==target: break
        if optimum(forced+[r],excluded)==target: forced.append(r)
        else: excluded.add(r['id'])
    return dict(selected=[r['id'] for r in forced],value=target)

def assignment(p,extra):
    jobs=array(obj(p)['jobs']); workers=array(p['workers']); distinct(jobs); distinct(workers)
    jobs=sorted(copy.deepcopy(jobs),key=lambda r:text(r['id']))
    workers=sorted(copy.deepcopy(workers),key=lambda r:text(r['id']))
    for j in jobs:
        text(j['skill']); integer(j['duration'],1)
    for w in workers:
        integer(w['capacity'],0); integer(w['cost'],0)
        for s in array(w['skills']): text(s)
        for k,v in obj(w['affinity']).items(): text(k); integer(v)
    for x in extra:
        x=unwrap(x)
        if 'selected' in x: workers=[w for w in workers if w['id'] in x['selected']]
        if 'makespan' in x:
            for w in workers: w['capacity']=min(w['capacity'],x['makespan'])
    remaining={w['id']:w['capacity'] for w in workers}; best=None
    def visit(i,score,cost,pairs):
        nonlocal best
        if i==len(jobs):
            candidate=(-score,cost,tuple(pairs))
            if best is None or candidate<best: best=candidate
            return
        j=jobs[i]
        for w in workers:
            if j['skill'] not in w['skills'] or remaining[w['id']]<j['duration']: continue
            remaining[w['id']]-=j['duration']
            visit(i+1,score+w['affinity'].get(j['id'],0),cost+w['cost']*j['duration'],pairs+[(j['id'],w['id'])])
            remaining[w['id']]+=j['duration']
    visit(0,0,0,[])
    if best is None: return dict(feasible=False,score=0,cost=0,assignments=[])
    return dict(feasible=True,score=-best[0],cost=best[1],assignments=[dict(job=j,worker=w) for j,w in best[2]])

def dag(p,extra=()):
    rows=array(obj(p)['nodes']); distinct(rows); nodes={text(r['id']):copy.deepcopy(r) for r in rows}
    for n,r in nodes.items():
        integer(r['duration'],0); deps=array(r['deps'])
        if len(set(deps))!=len(deps) or any(d not in nodes or d==n for d in deps): raise ValueError('invalid dependency')
        r['deps']=set(deps)
    for x in extra:
        x=unwrap(x)
        if 'feasible' in x:
            if not x['feasible']: return dict(blocked=True,waves=[],critical_path=[],makespan=0,earliest_finish={})
            groups=defaultdict(list)
            for a in x['assignments']:
                if a['job'] not in nodes: raise ValueError('unknown assigned job')
                groups[a['worker']].append(a['job'])
            for jobs in groups.values():
                jobs.sort()
                for a,b in zip(jobs,jobs[1:]): nodes[b]['deps'].add(a)
    done={}; paths={}; waves=[]
    while len(done)<len(nodes):
        ready=sorted(n for n,r in nodes.items() if n not in done and r['deps']<=done.keys())
        if not ready: raise ValueError('cycle')
        for n in ready:
            deps=nodes[n]['deps']
            if deps:
                parent=min(deps,key=lambda d:(-done[d],paths[d]))
                done[n]=done[parent]+nodes[n]['duration']; paths[n]=paths[parent]+[n]
            else: done[n]=nodes[n]['duration']; paths[n]=[n]
        waves.append(ready)
    end=min(done,key=lambda n:(-done[n],paths[n])) if done else None
    return dict(blocked=False,waves=waves,critical_path=paths[end] if end else [],makespan=done[end] if end else 0,earliest_finish=dict(sorted(done.items())))

def decode(p):
    data=obj(p); events=[]
    for raw in array(data['events']):
        r=json.loads(raw) if isinstance(raw,str) else obj(raw)
        r=obj(r)
        partition=text(r.get('partition',r.get('topic')))
        offset=integer(r.get('offset',r.get('sequence')),0)
        epoch=integer(r.get('epoch',r.get('generation',0)),0)
        committed=r.get('committed',r.get('ack',False))
        if type(committed) is not bool: raise ValueError('invalid committed')
        events.append(dict(partition=partition,offset=offset,epoch=epoch,committed=committed))
    # Checkpoint validation belongs to the replay package.
    return dict(events=sorted(events,key=lambda r:(r['partition'],r['offset'],r['epoch'],r['committed'])),checkpoints=copy.deepcopy(data['checkpoints']))

def settlement_decode(p):
    events=[]
    for raw in array(obj(p)['events']):
        r=json.loads(raw) if isinstance(raw,str) else obj(raw)
        events.append(dict(id=text(r['id']),revision=integer(r.get('revision',0),0),
            ts=integer(r.get('ts',r.get('timestamp')),0),key=text(r.get('key',r.get('account'))).lower(),
            value=number(r.get('value',r.get('amount')))))
    return dict(events=sorted(events,key=lambda r:(r['id'],r['revision'],r['ts'],r['key'],r['value'])))

def checkpoint(p):
    p=obj(p); checkpoints={}; events={}; checkpoint_versions={}; event_versions={}
    for r in array(p['checkpoints']):
        key=text(r['partition']); offset=integer(r['offset'],-1); epoch=integer(r['epoch'],0)
        version=(key,epoch)
        if version in checkpoint_versions and checkpoint_versions[version]!=offset: raise ValueError('checkpoint conflict')
        checkpoint_versions[version]=offset
        if key not in checkpoints or epoch>checkpoints[key][0]: checkpoints[key]=(epoch,offset)
    for r in array(p['events']):
        part=text(r['partition']); offset=integer(r['offset'],0); epoch=integer(r['epoch'],0)
        if type(r['committed']) is not bool: raise ValueError('invalid commit')
        key=(part,offset); val=(epoch,r['committed'])
        version=(part,offset,epoch)
        if version in event_versions and event_versions[version]!=val: raise ValueError('event conflict')
        event_versions[version]=val
        if key not in events or epoch>events[key][0]: events[key]=val
    parts=sorted(set(checkpoints)|{part for part,off in events}); applied=[]; offsets={}; pending={}
    for part in parts:
        epoch,off=checkpoints.get(part,(0,-1)); current=off+1
        while (part,current) in events and events[part,current][0]>=epoch and events[part,current][1]:
            applied.append(f'{part}:{current}'); current+=1
        offsets[part]=current
        pending[part]=sorted(o for (p,o),v in events.items() if p==part and o>=current)
    return dict(next_offsets=offsets,applied=applied,pending=pending)

def trace(p):
    p=obj(p); flat=[]
    def walk(r,parent=None):
        r=obj(r); item={k:v for k,v in r.items() if k!='children'}
        item['parent']=r.get('parent',parent); flat.append(item)
        for child in array(r.get('children',[])): walk(child,r['id'])
    for r in array(p['spans']): walk(r)
    distinct(flat); nodes={text(r['id']):r for r in flat}
    for ident,r in nodes.items():
        text(r['service']); number(r['duration'])
        if r['duration']<0 or type(r['error']) is not bool: raise ValueError('bad span')
        if r['parent'] is not None and r['parent'] not in nodes: raise ValueError('orphan span')
    graph={'nodes':[dict(id=n,duration=0,deps=[] if r['parent'] is None else [r['parent']]) for n,r in nodes.items()]}
    topo=dag(graph); ends={}; paths={}
    for wave in topo['waves']:
        for n in wave:
            parent=nodes[n]['parent']; ends[n]=(ends[parent] if parent else 0)+nodes[n]['duration']
            paths[n]=(paths[parent] if parent else [])+[n]
    end=min(ends,key=lambda n:(-ends[n],paths[n])) if ends else None
    return dict(error_services=sorted(set(r['service'].strip().lower() for r in nodes.values() if r['error'])),critical_path=paths[end] if end else [],duration=ends[end] if end else 0,span_count=len(nodes))

def logparse(p):
    lines=[]; counts=Counter()
    for raw in array(obj(p)['lines']):
        if isinstance(raw,str) and raw.lstrip().startswith('{'): raw=json.loads(raw)
        if isinstance(raw,str):
            parts=raw.strip().split(maxsplit=1)
            if not parts: continue
            level=parts[0]; message=parts[1] if len(parts)>1 else ''
        else:
            raw=obj(raw); level=raw.get('level',raw.get('severity')); message=raw.get('message',raw.get('msg'))
        level=text(level).lower()
        if level=='warning': level='warn'
        if level not in ('debug','info','warn','error'): raise ValueError('unknown log level')
        if not isinstance(message,str): raise ValueError('invalid message')
        message=re.sub(r'(?i)\b(token|password|secret)\s*=\s*("[^"]*"|\'[^\']*\'|[^\s,;]+)',lambda m:m.group(1).lower()+'=[REDACTED]',message)
        lines.append(level.upper()+' '+message); counts[level]+=1
    return dict(lines=lines,counts=dict(sorted(counts.items())))

def compatibility(p):
    p=obj(p); old=array(p['old']); new=array(p['new'])
    def index(rows):
        out={}
        for r in rows:
            field=text(r['name']); typ=r['type']; required=r['required']
            if typ not in ('int','float','str','bool') or type(required) is not bool or field in out: raise ValueError('invalid schema')
            out[field]=r
        return out
    a=index(old); b=index(new); changes=[]
    for field in sorted(a.keys()|b.keys()):
        if field not in b: changes.append(dict(field=field,code='removed',breaking=True))
        elif field not in a: changes.append(dict(field=field,code='added',breaking=b[field]['required'] and 'default' not in b[field]))
        else:
            if a[field]['type']!=b[field]['type']:
                changes.append(dict(field=field,code='type',breaking=(a[field]['type'],b[field]['type'])!=('int','float')))
            if not a[field]['required'] and b[field]['required']:
                changes.append(dict(field=field,code='required',breaking='default' not in b[field]))
    return dict(compatible=not any(c['breaking'] for c in changes),changes=changes)

def windows(p,c):
    rows=array(obj(p)['events']); width=integer(c['window_size'],1); latest={}; versions={}
    for r in rows:
        ident=text(r['id']); revision=integer(r['revision'],0); ts=integer(r['ts'],0)
        key=text(r['key']).lower(); value=number(r['value'])
        norm=dict(id=ident,revision=revision,ts=ts,key=key,value=value)
        version=(ident,revision)
        if version in versions and versions[version]!=norm: raise ValueError('event revision conflict')
        versions[version]=norm
        if ident not in latest or revision>latest[ident]['revision']: latest[ident]=norm
    groups=defaultdict(list)
    for r in latest.values(): groups[(r['ts']//width*width,r['key'])].append(r['value'])
    out=[]
    for (start,key),values in sorted(groups.items()):
        values.sort(); out.append(dict(start=start,end=start+width,key=key,count=len(values),sum=sum(values),p95=values[math.ceil(.95*len(values))-1]))
    return dict(windows=out,event_count=len(latest))

def graphimpact(p):
    p=obj(p); edges=array(p['edges']); seeds=sorted(set(text(s) for s in array(p['seeds']))); adj=defaultdict(set)
    for e in edges:
        if not isinstance(e,list) or len(e)!=2: raise ValueError('bad edge')
        a,b=map(text,e); adj[a].add(b); adj[b]
    for s in seeds: adj[s]
    distances={s:0 for s in seeds}; queue=deque(seeds)
    while queue:
        a=queue.popleft()
        for b in sorted(adj[a]):
            if b not in distances: distances[b]=distances[a]+1; queue.append(b)
    # Kosaraju with deterministic traversal, supports cycles and self loops.
    visited=set(); order=[]
    def dfs(a):
        visited.add(a)
        for b in sorted(adj[a]):
            if b not in visited: dfs(b)
        order.append(a)
    for a in sorted(adj):
        if a not in visited: dfs(a)
    rev=defaultdict(set)
    for a,bs in adj.items():
        for b in bs: rev[b].add(a)
    visited=set(); components=[]
    def collect(a,group):
        visited.add(a); group.append(a)
        for b in sorted(rev[a]):
            if b not in visited: collect(b,group)
    for a in reversed(order):
        if a not in visited:
            group=[]; collect(a,group); components.append(sorted(group))
    return dict(distances=dict(sorted(distances.items())),components=sorted(components))

def policy(p):
    p=obj(p); rules=array(p['rules']); distinct(rules); requests=array(p['requests']); decisions=[]
    for r in rules:
        integer(r['priority']); text(r['resource']); text(r['action'])
        if r['effect'] not in ('allow','deny'): raise ValueError('invalid effect')
    for req in requests:
        resource=text(req['resource']); action=text(req['action'])
        matches=[r for r in rules if fnmatch.fnmatchcase(resource,r['resource']) and fnmatch.fnmatchcase(action,r['action'])]
        def key(r):
            specificity=sum(ch not in '*?[]' for ch in r['resource']+r['action'])
            return (-r['priority'],-specificity,r['effect']!='deny',r['id'])
        winner=min(matches,key=key) if matches else None
        decisions.append(dict(resource=resource,action=action,effect=winner['effect'] if winner else 'deny',rule_id=winner['id'] if winner else None))
    return dict(decisions=decisions,allow=sum(d['effect']=='allow' for d in decisions),deny=sum(d['effect']=='deny' for d in decisions))

def evaluate(payloads,c):
    try:
        payloads=copy.deepcopy(array(payloads)); op=c['operation']; p=unwrap(payloads[0]) if payloads else None
        from strengthening import NEW_RULES, evaluate_new
        if op in NEW_RULES: result=evaluate_new(payloads,c)
        elif op.endswith('_evidence'): result=evidence(p,c)
        elif op=='risk_ranking': result=ranking(payloads,c)
        elif op=='review_balance': result=balancing(payloads,c)
        elif op=='remediation_plan': result=dependency_plan(payloads,c)
        elif op=='weighted_intervals': result=weighted(p,c)
        elif op=='capacity_assignment': result=assignment(p,payloads[1:])
        elif op=='critical_path': result=dag(p,payloads[1:])
        elif op=='event_decode': result=decode(p)
        elif op=='settlement_decode': result=settlement_decode(p)
        elif op=='checkpoint_replay': result=checkpoint(p)
        elif op=='trace_correlation': result=trace(p)
        elif op=='log_compatibility': result=logparse(p)
        elif op=='schema_compatibility': result=compatibility(p)
        elif op=='event_windows': result=windows(p,c)
        elif op=='dependency_impact': result=graphimpact(p)
        elif op=='policy_precedence': result=policy(p)
        else: raise ValueError('unknown operation')
        return dict(name=c['name'],result=result)
    except (KeyError,TypeError,IndexError,AttributeError,json.JSONDecodeError) as exc:
        raise ValueError('invalid payload') from exc

def final_report(core,title):
    raw=json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    attention=[]
    for name,r in core['components'].items():
        if r.get('blocked') or r.get('feasible') is False or r.get('compatible') is False or r.get('deny',0)>0 or r.get('score_total',0)>=20:
            attention.append(name)
    return dict(title=title,component_count=len(core['components']),sha256=hashlib.sha256(raw.encode('utf-8')).hexdigest(),attention=sorted(attention))
