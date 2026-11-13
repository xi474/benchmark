from itertools import product,combinations
from semantic import group


def operations(q,state):
    current=group(q,state);links={(e['from'],e['to']) for e in q['links']};containers={c['id']:c for c in q['containers']};answer=[]
    for i,s in enumerate(q['stacks']):
        if not state[i]:continue
        name=state[i][-1];c=containers[name]
        if name in current:answer.append(dict(kind='retrieve',container=name,**{'from':s['id'],'to':None}))
        for j,d in enumerate(q['stacks']):
            if (s['id'],d['id']) in links and len(state[j])<d['capacity'] and c['hazard'] in d['allowed_hazards']:answer.append(dict(kind='rehandle',container=name,**{'from':s['id'],'to':d['id']}))
    return answer


def batches(q,state):
    ops=operations(q,state)
    for size in range(1,min(len(q['cranes']),len(ops))+1):
        for chosen in combinations(ops,size):
            touched=[{o['from']}|({o['to']} if o['to'] is not None else set()) for o in chosen]
            if any(a&b for i,a in enumerate(touched) for b in touched[i+1:]):continue
            domains=[[c['id'] for c in q['cranes'] if touch<=set(c['reaches'])] for touch in touched]
            for cranes in product(*domains):
                if len(set(cranes))!=size:continue
                yield [dict(crane=c,**o) for c,o in zip(cranes,chosen)];break
