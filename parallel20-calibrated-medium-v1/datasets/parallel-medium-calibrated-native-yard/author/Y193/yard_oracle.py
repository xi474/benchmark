from collections import defaultdict,deque
from itertools import product,count
import heapq
from semantic import replay,infeasible


def crane_actions(q,state):
    remaining={c for row in state for c in row};allowed=next((set(g)&remaining for g in q['retrieval_groups'] if set(g)&remaining),set());containers={c['id']:c for c in q['containers']};links={(e['from'],e['to']) for e in q['links']};result=[]
    for crane in q['cranes']:
        actions=[];reach=set(crane['reaches'])
        for i,s in enumerate(q['stacks']):
            if s['id'] not in reach or not state[i]:continue
            c=state[i][-1]
            if c in allowed:actions.append(dict(crane=crane['id'],kind='retrieve',container=c,**{'from':s['id'],'to':None}))
            for j,d in enumerate(q['stacks']):
                if d['id'] in reach and (s['id'],d['id']) in links and len(state[j])<d['capacity'] and containers[c]['hazard'] in d['allowed_hazards']:actions.append(dict(crane=crane['id'],kind='rehandle',container=c,**{'from':s['id'],'to':d['id']}))
        result.append(actions)
    return result


def key(ops):return tuple(sorted((o['kind'],o['container'],o['from'],o['to'] or '') for o in ops))


def single(q,state):
    seen=set()
    for actions in crane_actions(q,state):
        for op in actions:
            k=key([op])
            if k not in seen:seen.add(k);yield [op]


def batches(q,state):
    seen=set()
    for choices in product(*([None]+actions for actions in crane_actions(q,state))):
        ops=[o for o in choices if o is not None]
        if not ops:continue
        touched=[]
        for o in ops:touched += [o['from']]+([o['to']] if o['to'] is not None else [])
        if len(set(touched))!=len(touched):continue
        k=key(ops)
        if k not in seen:seen.add(k);yield ops


def transition(q,state,ops,time=0):
    where={s['id']:i for i,s in enumerate(q['stacks'])};containers={c['id']:c for c in q['containers']};rows=[list(r) for r in state];cost=0;start=time;duration=0
    for o in ops:
        c=containers[o['container']];rows[where[o['from']]].pop();duration=max(duration,c['handling_ticks'])
        if o['kind']=='rehandle':rows[where[o['to']]].append(o['container']);cost+=c['rehandle_cost']
        else:start=max(start,c['appointment_tick'])
    return tuple(map(tuple,rows)),cost,start+duration,start


def solve(q):
    start=tuple(tuple(s['containers']) for s in q['stacks']);goal=tuple(() for _ in q['stacks']);seen={start};queue=deque([start]);reverse=defaultdict(list);serial=count()
    while queue:
        state=queue.popleft()
        for ops in single(q,state):
            following,cost,finish,begin=transition(q,state,ops);reverse[following].append((state,cost))
            if following not in seen:seen.add(following);queue.append(following)
    if goal not in seen:return infeasible(q)
    h={goal:0};heap=[(0,next(serial),goal)]
    while heap:
        cost,_,state=heapq.heappop(heap)
        if h[state]!=cost:continue
        for previous,added in reverse[state]:
            candidate=cost+added
            if previous not in h or candidate<h[previous]:h[previous]=candidate;heapq.heappush(heap,(candidate,next(serial),previous))
    best={start:0};parents={};heap=[(0,next(serial),start)]
    while heap:
        time,_,state=heapq.heappop(heap)
        if best[state]!=time:continue
        if state==goal:
            plans=[]
            while state in parents:state,batch=parents[state];plans.append(batch)
            answer=replay(q,list(reversed(plans)));assert answer['rehandle_cost']==h[start];return answer
        for ops in batches(q,state):
            following,cost,finish,begin=transition(q,state,ops,time)
            if following not in h or h[state]!=cost+h[following]:continue
            if following not in best or finish<best[following]:best[following]=finish;parents[following]=(state,dict(start=begin,operations=ops));heapq.heappush(heap,(finish,next(serial),following))
    raise AssertionError('optimal-cost serial path must be feasible')
