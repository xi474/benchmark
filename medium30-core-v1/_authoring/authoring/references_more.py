import copy
from datetime import datetime,timedelta
import re

def dt(s):return datetime.strptime(s,'%Y%m%dT%H%M%SZ')
def fmt(t):return t.strftime('%Y%m%dT%H%M%SZ')
def compose(a,b):return tuple(a[b[i]] for i in range(len(a)))
def closure(gs):
    identity=tuple(range(len(gs[0])));seen={identity};pending=[identity]
    for a in pending:
        for b in gs:
            v=compose(a,b)
            if v not in seen:seen.add(v);pending.append(v)
    return sorted(seen)

def blockmul(a,b):
    out=[]
    for i,row in enumerate(a):
        line=[]
        for j in range(len(b[0])):
            nr=a[i][0]['rows'];nc=b[0][j]['cols'];data=[[0]*nc for _ in range(nr)]
            for k in range(len(row)):
                aa=a[i][k];bb=b[k][j]
                if aa['data'] is None or bb['data'] is None:continue
                for r in range(nr):
                    for c in range(nc):data[r][c]+=sum(aa['data'][r][q]*bb['data'][q][c] for q in range(aa['cols']))
            line.append(dict(rows=nr,cols=nc,data=data if any(x for rr in data for x in rr) else None))
        out.append(line)
    return out

def more_solve(op,p,c):
    if op=='calendar_availability':
        busy=[(dt(a),dt(b)) for a,b in re.findall(r'DTSTART:(\d+T\d+Z)\s+DTEND:(\d+T\d+Z)',p['ics'])];rule=p['rule'];out=[]
        if rule['late_buffer']:
            busy=[(a,b+timedelta(minutes=rule['late_buffer']['minutes']) if b.hour*60+b.minute>=rule['late_buffer']['threshold'] else b) for a,b in busy]
        for day in p['days']:
            midnight=datetime.fromisoformat(day);end=min(rule['end'],rule['weekday_end'].get(str(midnight.weekday()),rule['end']))
            free=[(midnight+timedelta(minutes=rule['start']),midnight+timedelta(minutes=end))]
            cuts=busy+[(midnight+timedelta(minutes=a),midnight+timedelta(minutes=b)) for a,b in rule['breaks']]
            for a,b in sorted(cuts):
                nxt=[]
                for s,e in free:
                    if b<=s or a>=e:nxt.append((s,e))
                    else:
                        if s<a:nxt.append((s,a))
                        if b<e:nxt.append((b,e))
                free=nxt
            out.extend([[fmt(s),fmt(e)] for s,e in free if s<e])
        return sorted(out)
    if op=='meeting_intersection':
        free=[(dt(a),dt(b)) for a,b in p['alice']]
        for name in ['bob','carol']:free=[(max(a,dt(c)),min(b,dt(d))) for a,b in free for c,d in p[name] if max(a,dt(c))<min(b,dt(d))]
        start=min(a for a,b in free if b-a>=timedelta(hours=1))
        return dict(start=fmt(start),end=fmt(start+timedelta(hours=1)),attendees=p['attendees'],summary='Team Planning Meeting')
    if op=='group_closure':return [list(x) for x in closure(p['generators'])]
    if op=='homomorphism':
        e=tuple(range(len(p['generators'][0])));target_e=tuple(range(len(p['images'][0])));mapping={e:target_e};pending=[e]
        for a in pending:
            for g,h in zip(p['generators'],p['images']):
                b=compose(a,g);image=compose(mapping[a],h)
                if b in mapping and mapping[b]!=image:return dict(valid=False,mapping=[])
                if b not in mapping:mapping[b]=image;pending.append(b)
        return dict(valid=True,mapping=[dict(source=list(k),target=list(mapping[k])) for k in sorted(mapping)])
    if op=='block_layout':return dict(row_sizes=[row[0]['rows'] for row in p['matrix']],col_sizes=[b['cols'] for b in p['matrix'][0]])
    if op=='block_square':return blockmul(p['matrix'],p['matrix'])
    if op=='block_cube':return dict(layout=p['layout'],blocks=blockmul(p['squared'],p['matrix']))
    if op=='choice_base':return [copy.deepcopy(x) for x in p['entities'] if x['active']]
    if op=='choice_matches':return [x['entity'] for x in p['relations'] if x['funny'] and x['weight']>=p['minimum']]
    if op=='choice_join':return [dict(id=x['id'],label=x['name']) for x in p['candidates'] if x['id'] in set(p['matches'])]
    if op=='exempt_users':return sorted(name for name,groups in p['memberships'].items() if set(groups)&set(p['exempt_groups']))
    if op=='initial_queue':return sorted(copy.deepcopy(p['posts']),key=lambda x:x['id'])
    if op=='replay_moderation':
        topics=set(p['topics']);queue={x['id']:copy.deepcopy(x) for x in p['queue']};pub={}
        for e in p['events']:
            if e['kind']=='post':
                post={k:e[k] for k in ['id','tid','user']};(pub if e['user'] in p['exempt'] else queue)[e['id']]=post
            elif e['kind']=='merge':
                topics-=set(e['sources'])
                for x in list(queue.values())+list(pub.values()):
                    if x['tid'] in e['sources']:x['tid']=e['target']
            else:pub[e['id']]=queue.pop(e['id'])
        return dict(topics=sorted(topics),queue=sorted(queue.values(),key=lambda x:x['id']),published=sorted(pub.values(),key=lambda x:x['id']))
    from references_final import final_solve
    return final_solve(op,p,c)
