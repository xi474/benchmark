from functools import lru_cache
from itertools import combinations


def solve(q,independent=False,greedy=False):
    if independent:
        from dijkstra_oracle import solve as other
        return other(q)
    actions=sorted(q['actions'],key=lambda a:a['id']);index={a['id']:i for i,a in enumerate(actions)};n=len(actions)
    deps=[sum(1<<index[k] for k in a['deps']) for a in actions];children=[0]*n
    for i,mask in enumerate(deps):
        for j in range(n):
            if mask>>j&1:children[j]|=1<<i
    def batches(ready):
        if greedy:
            selected=[];used=set()
            for i in ready:
                if actions[i]['resource'] not in used:selected.append(i);used.add(actions[i]['resource'])
            return [tuple(selected)]
        return [batch for size in range(1,len(ready)+1) for batch in combinations(ready,size) if len({actions[i]['resource'] for i in batch})==len(batch)]
    @lru_cache(None)
    def rollback(success,attempts):
        done=0;unresolved=[]
        for i,a in enumerate(actions):
            if not success>>i&1:continue
            c=attempts[i]
            if c and (a['compensate'][c-1] or c==len(a['compensate'])):
                done|=1<<i
                if not a['compensate'][c-1]:unresolved.append(a['id'])
        if done==success:return 0,(),tuple(unresolved)
        ready=[i for i in range(n) if success>>i&1 and not done>>i&1 and not children[i]&success&~done]
        best=None;trace=None;bad=None
        for batch in batches(ready):
            next_attempts=list(attempts)
            for i in batch:next_attempts[i]+=1
            tail,following,failures=rollback(success,tuple(next_attempts));cost=max(actions[i]['compensation_time'] for i in batch)+tail
            if best is None or cost<best:best=cost;trace=(tuple(actions[i]['id'] for i in batch),)+following;bad=failures
        assert best is not None
        return best,trace,bad
    @lru_cache(None)
    def forward(attempts):
        success=sum(1<<i for i,a in enumerate(actions) if attempts[i] and a['forward'][attempts[i]-1])
        if success==(1<<n)-1:return 0,(),(),(),(), 'committed'
        ready=[i for i in range(n) if not success>>i&1 and attempts[i]<len(actions[i]['forward']) and deps[i]&success==deps[i]]
        best=None;answer=None
        for batch in batches(ready):
            revised=list(attempts);achieved=success;failed=[]
            for i in batch:
                revised[i]+=1;outcome=actions[i]['forward'][revised[i]-1]
                if outcome:achieved|=1<<i
                elif revised[i]==len(actions[i]['forward']):failed.append(actions[i]['id'])
            duration=max(actions[i]['forward_time'] for i in batch)
            if failed:
                rest,comp,unresolved=rollback(achieved,(0,)*n);candidate=(duration+rest,(tuple(actions[i]['id'] for i in batch),),comp,tuple(failed),unresolved,
                    'rollback_incomplete' if unresolved else 'rolled_back')
            else:
                cost,trace,comp,failures,unresolved,status=forward(tuple(revised));candidate=(duration+cost,(tuple(actions[i]['id'] for i in batch),)+trace,comp,failures,unresolved,status)
            if best is None or candidate[0]<best:best=candidate[0];answer=candidate
        assert answer is not None
        return answer
    initial=tuple(q.get('initial_attempts',{}).get(a['id'],0) for a in actions)
    cost,fwd,comp,failed,unresolved,status=forward(initial);forward.cache_clear();rollback.cache_clear()
    return dict(minimum_time=cost,forward_batches=[list(b) for b in fwd],compensation_batches=[list(b) for b in comp],
        status=status,failed_actions=list(failed),unresolved=list(unresolved))
