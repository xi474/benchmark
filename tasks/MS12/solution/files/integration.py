from functools import lru_cache
from math import prod

def combine(p, left, right):
    from collections import defaultdict
    leaves={tuple(h):w for h,w in left if w is not None};nodes=[tuple(h) for h,_ in left]
    children=defaultdict(list)
    for k in nodes:children[k[:-1]].append(k)
    groups=p['groups']
    recipes={r['id']:r for r in p['recipes']}
    options={h:[recipes[k] for k in right[h[-1]]] for h in nodes}
    def combine(parts):
        u,c,n=0,0,1;menu={};allowed={}
        for a,b,k,m,values in parts:
            u+=a;c+=b;n*=k;menu.update(m);allowed.update(values)
        return u,c,n,menu,allowed
    for floor in range(len(next(iter(leaves))),-1,-1):
        def solve(h,used,last,spend,sat):
            best=None
            for r in options[h]:
                rid=r['id'];cat=r['cat'];pay=spend+r['cost']
                if rid in used or cat==last or pay>p['budget']:continue
                updated=tuple(v+int(cat in g[3]) for v,g in zip(sat,groups))
                if h in leaves:
                    if min(updated)<floor:continue
                    u=leaves[h]*sum(z*g[1] for z,g in zip(updated,groups))
                    result=(u,leaves[h]*pay,1,{}, {})
                else:
                    parts=[solve(k,used|{rid},cat,pay,updated) for k in children[h]]
                    if any(z is None for z in parts):continue
                    result=combine(parts)
                u,c,n,m,a=result;m[h]=rid;a[h]={rid}
                if best is None or (u,-c)>(best[0],-best[1]):best=(u,c,n,m,a)
                elif (u,c)==best[:2]:
                    b=best
                    lex=lambda menu:tuple(menu[k] for k in sorted(menu))
                    best=(u,c,n+b[2],min([b[3],m],key=lex),{k:a[k]|b[4][k] for k in a})
            return best
        branches=[solve(k,set(),None,0,(0,)*len(groups)) for k in children[()]]
        if all(v is not None for v in branches):
            u,c,n,m,a=combine(branches)
            return dict(histories=list(map(list,nodes)),optimal=dict(floor=floor,utility=u,cost=c,count=n,
                        menu=[m[k] for k in nodes],allowed=[sorted(a[k]) for k in nodes]))
    return dict(histories=list(map(list,nodes)),optimal=None)

from pathlib import Path
import json

