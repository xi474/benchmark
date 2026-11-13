from heapq import heappop,heappush
from itertools import count
from semantic import initial_state,terminal,all_batches


def solve(q):
    serial=count();start=initial_state(q);dist={start:0};predecessor={};queue=[(0,next(serial),start)]
    while queue:
        value,_,state=heappop(queue)
        if dist[state]!=value:continue
        finish=terminal(q,state)
        if finish is not None:
            trail=[];cursor=state
            while cursor!=start:
                previous,batch,failed=predecessor[cursor];trail.append((previous[0],batch,failed));cursor=previous
            trail.reverse();failures=[k for phase,batch,failed in trail for k in failed]
            return dict(minimum_time=value,forward_batches=[list(batch) for phase,batch,failed in trail if phase=='forward'],
                compensation_batches=[list(batch) for phase,batch,failed in trail if phase=='rollback'],status=finish[0],failed_actions=failures,unresolved=finish[1])
        for batch,following,elapsed,failed in all_batches(q,state):
            revised=value+elapsed
            if revised<dist.get(following,float('inf')):
                dist[following]=revised;predecessor[following]=(state,batch,failed);heappush(queue,(revised,next(serial),following))
    raise AssertionError('Valid finite saga has no terminal trace')
