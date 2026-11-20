#!/bin/bash
set -eu
cd /app
cat > solution.py <<'MEDIUM69_REFERENCE'
from fractions import Fraction
from math import prod

def transform(p):
    out=[]
    for cancelled in p['withdrawals']:
        slots={k:(t,q) for k,t,q in p['slots'] if k not in cancelled}
        terms={k:(n,{s for s in names if s in slots and due-7<=slots[s][0]<due})
               for k,due,n,names in p['assignments'] if due is not None}
        if not terms:out.append(dict(empty=True));continue
        missing=sorted(k for k,(n,s) in terms.items() if not s)
        if missing:out.append(dict(unserved=missing));continue
        pending=set(terms);regions=[]
        while pending:
            work=[pending.pop()];grp=set(work)
            while work:
                k=work.pop()
                neighbours={s for s in pending if terms[k][1]&terms[s][1]}
                pending-=neighbours;grp|=neighbours;work.extend(neighbours)
            grp=sorted(grp);top=0;wins=[]
            def dfs(i,demand,days,mask):
                nonlocal top,wins
                if i==len(grp):
                    if mask:
                        v=Fraction(demand,sum(slots[s][1] for s in days))
                        if v>top:top=v;wins=[]
                        if v==top:wins.append(mask)
                    return
                d,s=terms[grp[i]]
                dfs(i+1,demand,days,mask);dfs(i+1,demand+d,days|s,mask|1<<i)
            dfs(0,0,set(),0);regions.append((top,grp,wins))
        peak=max(r[0] for r in regions);count=1;minimal=[];implies=[]
        for top,grp,wins in regions:
            if top!=peak:continue
            count*=1+len(wins)
            unique=[]
            for m in sorted(wins,key=int.bit_count):
                if not any(t&m==t for t in unique):unique.append(m)
            minimal.extend([[k for j,k in enumerate(grp) if m>>j&1] for m in unique])
            for j,k in enumerate(grp):
                containing=[v for v in wins if v>>j&1]
                if containing:implies.append([k,[name for idx,name in enumerate(grp) if name!=k and all(v>>idx&1 for v in containing)]])
        out.append(dict(peak=[peak.numerator,peak.denominator],count=count-1,
                        minimal=sorted(minimal,key=lambda v:(len(v),v)),implies=sorted(implies)))
    return out

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
