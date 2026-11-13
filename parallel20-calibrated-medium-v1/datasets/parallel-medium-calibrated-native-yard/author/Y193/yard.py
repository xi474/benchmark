import heapq
from itertools import count
from semantic import initial,step,replay,infeasible,group
from yard_moves import batches,operations


def solve(q,independent=False,greedy=False):
    if independent:
        from yard_oracle import solve as other
        return other(q)
    containers={c['id']:c for c in q['containers']};state=initial(q);serial=count()
    def earliest(time,ops):return max([time]+[containers[o['container']]['appointment_tick'] for o in ops if o['kind']=='retrieve'])
    if greedy:
        plans=[];time=0;seen=set()
        while any(state):
            if state in seen:return infeasible(q)
            seen.add(state);current=group(q,state);chosen=None
            available=operations(q,state)
            targets=sorted(current)
            for name in targets:
                i=next(i for i,row in enumerate(state) if name in row);top=state[i][-1]
                choices=[o for o in available if o['container']==top and ((top==name and o['kind']=='retrieve') or top!=name and o['kind']=='rehandle')]
                if choices:
                    op=min(choices,key=lambda o:(0 if o['to'] is None else len(state[next(j for j,s in enumerate(q['stacks']) if s['id']==o['to'])]),o['to'] or ''))
                    touch={op['from']}|({op['to']} if op['to'] else set());crane=next((c['id'] for c in q['cranes'] if touch<=set(c['reaches'])),None)
                    if crane is not None:chosen=[dict(crane=crane,**op)];break
            if chosen is None:
                fallback=sorted((o for o in available if o['kind']=='rehandle'),key=lambda o:(len(state[next(j for j,s in enumerate(q['stacks']) if s['id']==o['to'])]),o['from'],o['to']))
                for op in fallback:
                    touch={op['from'],op['to']};crane=next((c['id'] for c in q['cranes'] if touch<=set(c['reaches'])),None)
                    if crane is not None:chosen=[dict(crane=crane,**op)];break
            if chosen is None:return infeasible(q)
            batch=dict(start=earliest(time,chosen),operations=chosen);state,time,cost,done=step(q,state,time,batch);plans.append(batch)
        return replay(q,plans)
    dist={state:(0,0)};parent={};heap=[(0,0,next(serial),state)]
    while heap:
        cost,time,_,state=heapq.heappop(heap)
        if dist[state]!=(cost,time):continue
        if not any(state):
            plans=[]
            while state in parent:state,batch=parent[state];plans.append(batch)
            return replay(q,list(reversed(plans)))
        for ops in batches(q,state):
            batch=dict(start=earliest(time,ops),operations=ops);following,finish,added,done=step(q,state,time,batch);score=(cost+added,finish)
            if following not in dist or score<dist[following]:dist[following]=score;parent[following]=(state,batch);heapq.heappush(heap,(*score,next(serial),following))
    return infeasible(q)
