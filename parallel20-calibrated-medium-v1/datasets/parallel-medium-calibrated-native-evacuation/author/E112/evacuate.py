from collections import deque
from functools import lru_cache
from itertools import combinations,count
import heapq
from semantic import fire_grid,safe,conflict,report


def solve(q,independent=False,greedy=False):
    if independent:
        from flow_mip import solve as other
        return other(q)
    fire=fire_grid(q);people={e['id']:e for e in q['evacuees']};shelters={s['id']:s for s in q['shelters']};serial=count()
    @lru_cache(None)
    def path(name,vertices=frozenset(),edges=frozenset(),forbidden=frozenset()):
        e=people[name];start=(e['r'],e['c']);release=e['release']
        if not safe(q,fire,start,release) or (release,start) in vertices:return None
        queue=deque([(release,start)]);parents={(release,start):None}
        while queue:
            t,p=queue.popleft()
            options=[s for s in shelters.values() if s['id'] in e['eligible_shelters'] and s['id'] not in forbidden and s['capacity'] and (s['r'],s['c'])==p and s['opens']<=t<s['closes']]
            if options:
                trail=[];state=(t,p)
                while state is not None:trail.append(list(state[1]));state=parents[state]
                return dict(shelter=options[0]['id'],arrival=t,release=release,path=list(reversed(trail)))
            if t==q['max_ticks']:continue
            r,c=p
            for nxt in [p,(r-1,c),(r+1,c),(r,c-1),(r,c+1)]:
                state=(t+1,nxt)
                if state not in parents and safe(q,fire,nxt,t+1) and state not in vertices and (t,p,nxt) not in edges:parents[state]=(t,p);queue.append(state)
        return None
    empty=(frozenset(),frozenset(),frozenset())
    if greedy:
        plans={}
        for e in sorted(people.values(),key=lambda e:(e['release'],e['id'])):
            forbidden=frozenset(s for s,row in shelters.items() if sum(p['shelter']==s for p in plans.values())>=row['capacity']);candidate=path(e['id'],forbidden=forbidden)
            if candidate is not None and conflict(q,{**plans,e['id']:candidate}) is None:plans[e['id']]=candidate
        return report(q,fire,plans)
    for size in range(min(len(people),sum(s['capacity'] for s in shelters.values())),-1,-1):
        heap=[];seen=set()
        def push(constraints,plans):
            key=tuple(sorted(constraints.items()))
            if key in seen:return
            seen.add(key);heapq.heappush(heap,(sum(p['arrival'] for p in plans.values()),next(serial),constraints,plans))
        for chosen in combinations(people,size):
            plans={k:path(k) for k in chosen}
            if all(p is not None for p in plans.values()):push({k:empty for k in chosen},plans)
        while heap:
            cost,_,constraints,plans=heapq.heappop(heap);bad=conflict(q,plans)
            if bad is None:return report(q,fire,plans)
            kind,names,data=bad
            for name in names:
                vertices,edges,forbidden=constraints[name]
                if kind=='vertex':vertices=vertices|{data}
                elif kind=='shelter':forbidden=forbidden|{data}
                else:
                    t,u,v=data
                    if name==names[1]:u,v=v,u
                    edges=edges|{(t,u,v)}
                changed=(vertices,edges,forbidden);replacement=path(name,*changed)
                if replacement is not None:push({**constraints,name:changed},{**plans,name:replacement})
    raise AssertionError('empty evacuation is feasible')
