import heapq
from collections import Counter


def fire_grid(q):
    grid=q['grid'];h=len(grid);w=len(grid[0]);dist={};queue=[]
    for s in q['fire_seeds']:
        p=(s['r'],s['c']);t=s['time']
        if grid[p[0]][p[1]]!='#' and t<dist.get(p,float('inf')):dist[p]=t;heapq.heappush(queue,(t,p))
    while queue:
        t,(r,c)=heapq.heappop(queue)
        if dist[r,c]!=t:continue
        for u,v in [(r-1,c),(r+1,c),(r,c-1),(r,c+1)]:
            if 0<=u<h and 0<=v<w and grid[u][v]!='#':
                nt=t+q['spread_cost'][u][v]
                if nt<dist.get((u,v),float('inf')):dist[u,v]=nt;heapq.heappush(queue,(nt,(u,v)))
    return [[None if grid[r][c]=='#' else dist.get((r,c)) for c in range(w)] for r in range(h)]


def safe(q,fire,p,t):
    r,c=p
    return 0<=r<len(q['grid']) and 0<=c<len(q['grid'][0]) and q['grid'][r][c]!='#' and (fire[r][c] is None or t<fire[r][c]) and not any(e['r']==r and e['c']==c and e['start']<=t<=e['end'] for e in q['closures'])


def conflict(q,plans):
    names=list(plans)
    for t in range(q['max_ticks']+1):
        at={k:tuple(p['path'][t-p['release']]) for k,p in plans.items() if p['release']<=t<=p['arrival']}
        for i,k in enumerate(names):
            for j in names[i+1:]:
                if k in at and j in at and at[k]==at[j]:return ('vertex',(k,j),(t,at[k]))
                if t>0 and k in at and j in at and plans[k]['release']<t and plans[j]['release']<t:
                    oldk=tuple(plans[k]['path'][t-1-plans[k]['release']]);oldj=tuple(plans[j]['path'][t-1-plans[j]['release']])
                    if oldk==at[j] and oldj==at[k] and oldk!=at[k]:return ('edge',(k,j),(t-1,oldk,at[k]))
    for s in q['shelters']:
        users=[k for k,p in plans.items() if p['shelter']==s['id']]
        if len(users)>s['capacity']:return ('shelter',tuple(users[:s['capacity']+1]),s['id'])
    return None


def report(q,fire,plans):
    used=Counter(p['shelter'] for p in plans.values())
    return dict(max_saved=len(plans),total_arrival=sum(p['arrival'] for p in plans.values()),fire_arrival=fire,
        evacuees=[dict(id=e['id'],status='assigned',shelter=plans[e['id']]['shelter'],arrival=plans[e['id']]['arrival'],path=plans[e['id']]['path']) if e['id'] in plans else dict(id=e['id'],status='unassigned',shelter=None,arrival=None,path=[]) for e in q['evacuees']],
        shelters=[dict(id=s['id'],used=used[s['id']],capacity=s['capacity']) for s in q['shelters']])


def normalize(ident,value):return value


def check_value(task,component,actual,expected,request=None):
    try:
        q=request.get('request',request);fire=fire_grid(q)
        if set(actual)!=set(expected) or actual['max_saved']!=expected['max_saved'] or actual['total_arrival']!=expected['total_arrival'] or actual['fire_arrival']!=fire:return False
        people={e['id']:e for e in q['evacuees']};shelters={s['id']:s for s in q['shelters']};plans={}
        if len(actual['evacuees'])!=len(people) or {e['id'] for e in actual['evacuees']}!=set(people):return False
        for row in actual['evacuees']:
            e=people[row['id']]
            if row['status']=='unassigned':
                if row['shelter'] is not None or row['arrival'] is not None or row['path']!=[]:return False
                continue
            if row['status']!='assigned' or row['shelter'] not in e['eligible_shelters']:return False
            s=shelters[row['shelter']];t=row['arrival'];path=row['path']
            if not e['release']<=t<=q['max_ticks'] or not s['opens']<=t<s['closes'] or len(path)!=t-e['release']+1 or path[0]!=[e['r'],e['c']] or path[-1]!=[s['r'],s['c']]:return False
            if any(not safe(q,fire,p,e['release']+i) for i,p in enumerate(path)):return False
            if any(abs(a[0]-b[0])+abs(a[1]-b[1])>1 for a,b in zip(path,path[1:])):return False
            plans[e['id']]={**row,'release':e['release']}
        if conflict(q,plans) is not None:return False
        gold=report(q,fire,plans)
        return actual['max_saved']==gold['max_saved'] and actual['total_arrival']==gold['total_arrival'] and sorted(actual['shelters'],key=lambda e:e['id'])==sorted(gold['shelters'],key=lambda e:e['id'])
    except (TypeError,ValueError,KeyError,AttributeError,IndexError):return False
