from functools import lru_cache

def minimal(sets):
    kept=[]
    for s in sorted(set(sets),key=lambda v:(len(v),sorted(v))):
        if not any(t<=s for t in kept):kept.append(s)
    return kept

def merge(a,b):
    return minimal(x|y for x in a for y in b)

def combine(p, left, right):
    graph=right;ans=[]
    for qi,q in enumerate(p['queries']):
        inc=[];open_at={};allways=[frozenset()]
        for t in range(q['start'],q['end']):
            down_domains=set(left[qi][t-q['start']])
            @lru_cache(None)
            def ways(v):
                if v not in graph:return [frozenset()] if v not in down_domains else [frozenset([v])]
                k,children=graph[v];dp=[[frozenset()]]+[[] for _ in range(k)]
                for child in children:
                    choices=ways(child)
                    for j in range(k,0,-1):dp[j]=minimal(dp[j]+merge(dp[j-1],choices))
                return dp[k]
            for v in q['targets']:
                sets=ways(v);down=frozenset() not in sets
                if down and v not in open_at:open_at[v]=t
                if not down and v in open_at:inc.append([v,open_at.pop(v),t])
                allways=merge(allways,sets)
        inc.extend([v,s,q['end']] for v,s in open_at.items())
        ans.append(dict(incidents=sorted(inc),repairs=sorted([sorted(s) for s in allways],key=lambda s:(len(s),s))))
    return ans

from pathlib import Path
import json

