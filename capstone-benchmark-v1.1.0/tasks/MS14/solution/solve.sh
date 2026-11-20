#!/bin/bash
set -eu
cd /app
cat > solution.py <<'MEDIUM69_REFERENCE'
from functools import lru_cache

def minimal(sets):
    kept=[]
    for s in sorted(set(sets),key=lambda v:(len(v),sorted(v))):
        if not any(t<=s for t in kept):kept.append(s)
    return kept

def merge(a,b):
    return minimal(x|y for x in a for y in b)

def transform(p):
    graph={s['id']:s for s in p['services']};ans=[]
    for q in p['queries']:
        inc=[];open_at={};allways=[frozenset()]
        for t in range(q['start'],q['end']):
            events={}
            for d,at,seen,state in p['log']:
                if seen<=q['as_of'] and at<=t and (at,seen)>events.get(d,(-1,-1,''))[:2]:events[d]=(at,seen,state)
            @lru_cache(None)
            def ways(v):
                if v not in graph:return [frozenset()] if events.get(v,(0,0,'up'))[2]=='up' else [frozenset([v])]
                node=graph[v];k=node['need'];dp=[[frozenset()]]+[[] for _ in range(k)]
                for child in node['inputs']:
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

def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value

MEDIUM69_REFERENCE
