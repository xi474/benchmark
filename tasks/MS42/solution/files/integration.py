from fractions import Fraction
from itertools import permutations


def combine(p, left, right):
    full,tags=left;permits={(a,b):mask for a,opts in tags.items() for b,mask in opts.items()}
    pairs=[]
    def restore(name):
        rows,reach=right[name]
        return [(i,l,Fraction(*v),n) for i,l,v,n in rows],reach
    def add(table,key,n,mandatory):
        if key in table:
            prev,inter=table[key];table[key]=prev+n,inter&mandatory
        else:table[key]=n,mandatory
    def prune(table):
        best={}
        for mask,rank,sums in table:best[mask]=max(best.get(mask,(-1,-1)),rank)
        return {k:v for k,v in table.items() if k[1]==best[k[0]]}
    z=(0,0,0,0);global_states={(full,(0,0),z):(1,0)}
    for name in sorted(p['courses']):
        if not name.endswith('-2013J') or name[:-6]+'-2014J' not in p['courses']:continue
        prefix=name[:-6]
        lhs,L=restore(name);rhs,R=restore(prefix+'-2014J')
        token={}
        for l,_,_,_ in lhs:
            for r,_,_,_ in rhs:
                token[l,r]=1<<len(pairs);pairs.append([prefix,l,r])
        local={}
        def visit(i,mask,links,used,support,sums,bits):
            if i==len(lhs):
                add(local,(mask,(len(links),support),sums),1,bits);return
            visit(i+1,mask,links,used,support,sums,bits)
            l,a,ls,ln=lhs[i]
            for r,b,rs,rn in rhs:
                viable=mask&permits[a,b]
                if not viable or r in used:continue
                if any(((y in L[l])!=(t in R[r]) or (l in L[y])!=(r in R[t])) for y,t in links):continue
                news=tuple(x+y for x,y in zip(sums,(ls,ln,rs,rn)))
                visit(i+1,viable,links+[(l,r)],used|{r},support+min(ln,rn),news,bits|token[l,r])
        visit(0,full,[],set(),0,z,0)
        next_states={}
        options=prune(local)
        for (mask,rank,sums),(n,bits) in global_states.items():
            for (valid,rk,ss),(count,tags) in options.items():
                meet=mask&valid
                if not meet:continue
                key=(meet,tuple(a+b for a,b in zip(rank,rk)),tuple(a+b for a,b in zip(sums,ss)))
                add(next_states,key,n*count,bits|tags)
        global_states=prune(next_states)
    top=max(rank for _,rank,_ in global_states)
    ways=0;common=(1<<len(pairs))-1;drifts=[]
    for (_,rank,(os,on,ns,nn)),(n,required) in global_states.items():
        if rank!=top:continue
        ways+=n;common&=required
        if on:drifts.append(Fraction(ns,nn)-Fraction(os,on))
    def frac(x):return [x.numerator,x.denominator]
    return dict(pairs=top[0],support=top[1],ways=ways,forced=sorted(pair for i,pair in enumerate(pairs) if common>>i&1),
                drift=[frac(min(drifts)),frac(max(drifts))] if drifts else None)

from pathlib import Path
import json

