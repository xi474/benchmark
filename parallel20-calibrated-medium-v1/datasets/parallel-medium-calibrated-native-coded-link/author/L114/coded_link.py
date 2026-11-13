from functools import lru_cache
from coded_choices import options
from semantic import replay


def solve(q,independent=False,greedy=False):
    if independent:
        from symbol_oracle import solve as other
        return other(q)
    ps=q['packets'];stations=sorted({c['station'] for c in q['contacts']});end=max(c['end'] for c in q['contacts']);chosen={}
    def terminal(bs):return (sum(p['priority'] for p,b in zip(ps,bs) if len(b)==p['dimension']),sum(len(b)==p['dimension'] for p,b in zip(ps,bs)),sum(map(len,bs)))
    @lru_cache(None)
    def value(t,bs,h):
        if t==end:return terminal(bs)
        best=None;decision=None
        for after,hist,rows in options(q,t,bs,h,stations):
            score=terminal(after) if greedy else value(t+1,after,hist)
            if best is None or score>best:best=score;decision=(after,hist,rows)
        chosen[t,bs,h]=decision;return best
    bs=tuple(() for _ in ps);h=tuple((None,-1) for _ in stations);rows=[]
    if not greedy:value(0,bs,h)
    for t in range(end):
        if greedy:value(t,bs,h)
        bs,h,current=chosen[t,bs,h];rows.extend(current)
    return replay(q,rows)
