#!/bin/bash
set -eu
cd /app
cat > solution.py <<'MEDIUM69_REFERENCE'
from functools import lru_cache


def transform(payload):
    p=payload; topics=p["topics"]; papers=sorted(p["papers"],key=lambda r:r["id"])
    if not topics:
        return {"review":[],"graph":[list(e) for e in sorted(set(map(tuple,p["graph"])))]}
    offers=[]
    for topic in topics:
        row={}
        for j,paper in enumerate(papers):
            values=[q for t,section,q in paper["claims"] if t==topic and section in paper["methods"]]
            if values:row[j]=max(values)
        offers.append(row)
    def assign(floor):
        @lru_cache(None)
        def step(t,used):
            if t==len(topics):return 0,()
            out=[]
            for j,q in offers[t].items():
                if q<floor or used&(1<<j):continue
                tail=step(t+1,used|(1<<j))
                if tail is not None:out.append((tail[0]-q,(j,)+tail[1]))
            return min(out) if out else None
        return step(0,0)
    for floor in sorted({q for row in offers for q in row.values()},reverse=True):
        plan=assign(floor)
        if plan is not None:
            rows=[[topics[i],papers[j]["id"],offers[i][j]] for i,j in enumerate(plan[1])]
            edges={tuple(e) for e in p["graph"]}|{(paper,"supports",t) for t,paper,q in rows}
            return {"review":rows,"graph":[list(e) for e in sorted(edges)]}
    return None

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
