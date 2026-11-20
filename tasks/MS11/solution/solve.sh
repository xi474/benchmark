#!/bin/bash
set -eu
cd /app
cat > solution.py <<'MEDIUM69_REFERENCE'
from collections import defaultdict
from functools import lru_cache


def transform(p):
    students = sorted(p['students'])
    buyers = sorted(p['buyers'])
    g = defaultdict(list)
    for student, course, score in p['grades']:
        if course in (1, 2) and score is not None:
            g[student].append(score)
    x = {s: sum(g[s])*100//len(g[s]) for s in students}
    y = {b:0 for b in buyers}
    for order in p['orders']:
        for cats,n,price in order['lines']:
            if set(cats)&{'Cameras','Electronics'}:
                y[order['buyer']]+=n*price
    def report(drop):
        obs = defaultdict(dict)
        for src,s,b,v in p['evidence']:
            if src != drop:
                obs[s,b][src] = max(v,obs[s,b].get(src,0))
        w = {edge:sum(a.values()) for edge,a in obs.items()}
        links = {s:{b for t,b in w if t==s} for s in students}
        todo=set(students)
        groups=[]
        while todo:
            ss={min(todo)}
            while True:
                bb=set().union(*(links[s] for s in ss))
                nxt=ss|{s for s in todo if links[s]&bb}
                if ss==nxt:break
                ss=nxt
            if len(ss)!=len(bb):return None
            groups.append((sorted(ss),sorted(bb)))
            todo-=ss
        def local(ss,bb,threshold):
            @lru_cache(None)
            def visit(i,mask):
                if i==len(ss):return (0,1,0,(),0,(),frozenset())
                s=ss[i];best=None
                for j,b in enumerate(bb):
                    if mask>>j&1 or w.get((s,b),0)<threshold:continue
                    tail=visit(i+1,mask|(1<<j))
                    if tail is None:continue
                    z=x[s]*y[b]
                    a=(w[s,b]+tail[0],tail[1],z+tail[2],(b,)+tail[3],z+tail[4],(b,)+tail[5],tail[6]|{(s,b)})
                    if best is None or a[0]>best[0]:best=a
                    elif a[0]==best[0]:
                        mn=min((a[2],a[3]),(best[2],best[3]))
                        mx=min((-a[4],a[5]),(-best[4],best[5]))
                        best=(a[0],a[1]+best[1],mn[0],mn[1],-mx[0],mx[1],a[6]&best[6])
                return best
            return visit(0,0)
        vals=sorted(set(w.values()))
        lo,hi=-1,len(vals)
        while hi-lo>1:
            mid=(lo+hi)//2
            if all(local(s,b,vals[mid]) is not None for s,b in groups):lo=mid
            else:hi=mid
        if lo<0:return None
        floor=vals[lo];total=mn=mx=0;count=1;left={};right={};forced=[]
        for ss,bb in groups:
            t,c,a,av,b,bv,f=local(ss,bb,floor)
            total+=t;count*=c;mn+=a;mx+=b;left.update(zip(ss,av));right.update(zip(ss,bv));forced.extend(f)
        offset=sum(x.values())*sum(y.values())
        return dict(floor=floor,total=total,count=count,min_num=len(x)*mn-offset,max_num=len(x)*mx-offset,
                    min_buyers=[left[s] for s in students],max_buyers=[right[s] for s in students],
                    forced=[list(z) for z in sorted(forced)])
    return [dict(drop=d,result=report(d)) for d in p['drop']]

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
