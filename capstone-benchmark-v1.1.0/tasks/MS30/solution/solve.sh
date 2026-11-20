#!/bin/bash
set -eu
cd /app
cat > solution.py <<'MEDIUM69_REFERENCE'
from collections import Counter,defaultdict
from fractions import Fraction as F
from itertools import product

def transform(p):
    g=defaultdict(list)
    for s,c,v,full in p['grades']:
        if c in (16,17) and v is not None:g[s].append(F(v,full))
    tier={s:('P' if sum(y)*4>=3*len(y) else 'D' if sum(y)*5>=3*len(y) else 'N') for s,y in g.items()}
    last=max(r[1] for r in p['market'])
    ranked=sorted([row for row in p['market'] if row[1]>=last-29],key=lambda r:(-F(abs(r[3]-r[2]),r[2]),r[0]))[:p['top']]
    answers=[]
    for cancel in p['cancel']:
        avail={k for k,*_ in ranked if k not in cancel and p['rooms'][k]['capacity']}
        prefs={s:{k:n for n,group in enumerate(p['prefs'].get(s,[])) for k in group if k in avail} for s in g}
        prior={k:{t:n for n,group in enumerate(p['rooms'][k]['tiers']) for t in group} for k in avail}
        choices={s:{k for k in prefs[s] if tier[s] in prior[k]} for s in g}
        un=set(g);dist={0:1};forced=[];bestmap={}
        while un:
            group={min(un)}
            while True:
                rooms=set().union(*(choices[s] for s in group))
                other={s for s in un if choices[s]&rooms}-group
                if not other:break
                group|=other
            un-=group;ss=sorted(group);hist=Counter();maxn=-1;required=set();canonical=None
            for vals in product(*([*sorted(choices[s]),''] for s in ss)):
                by=defaultdict(list)
                for s,k in zip(ss,vals):
                    if k:by[k].append(prior[k][tier[s]])
                if any(len(v)>p['rooms'][k]['capacity'] for k,v in by.items()):continue
                block=any((not old or prefs[s][k]<prefs[s][old]) and
                    (len(by[k])<p['rooms'][k]['capacity'] or any(prior[k][tier[s]]<v for v in by[k]))
                    for s,old in zip(ss,vals) for k in choices[s] if k!=old)
                if block:continue
                count=sum(map(bool,vals));hist[count]+=1
                edges={(s,k) for s,k in zip(ss,vals) if k}
                if count>maxn:maxn=count;canonical=vals;required=edges
                elif count==maxn:canonical=min(canonical,vals);required&=edges
            nxt=Counter()
            for a,n in dist.items():
                for b,v in hist.items():nxt[a+b]+=n*v
            dist=nxt;bestmap.update(zip(ss,canonical));forced.extend(required)
        answers.append(dict(sizes=[list(v) for v in sorted(dist.items())],forced=[list(v) for v in sorted(forced)],
                            example=[bestmap[s] for s in sorted(g)]))
    return answers

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
