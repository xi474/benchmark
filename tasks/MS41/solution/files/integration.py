from fractions import Fraction as F
from functools import lru_cache


def solve(matrix, values):
    a=[left.copy()+right.copy() for left,right in zip(matrix,values)]
    n=len(a)
    for k in range(n):
        pivot=next(i for i in range(k,n) if a[i][k])
        a[k],a[pivot]=a[pivot],a[k]
        lead=a[k][k];a[k]=[x/lead for x in a[k]]
        for i in range(n):
            if i!=k and a[i][k]:
                multiple=a[i][k];a[i]=[x-multiple*y for x,y in zip(a[i],a[k])]
    return [r[n:] for r in a]


def single(graph,start,answers):
    nans=len(answers);alive=set(answers)
    while True:
        grown=alive|{s for s,edges in graph.items() if any(v in alive for v,_,_ in edges)}
        if grown==alive:break
        alive=grown
    names=sorted(alive-set(answers));idx={s:i for i,s in enumerate(names)}
    n=len(names);zero=[F(0)]*nans
    if start not in idx:return zero,zero
    mat=[[F(i==j) for j in range(n)] for i in range(n)]
    rhs=[zero.copy() for _ in names]
    trans=[]
    for i,s in enumerate(names):
        total=sum(w for _,w,_ in graph[s]);row=[]
        for v,w,c in graph[s]:
            pr=F(w,total);row.append((v,pr,c))
            if v in idx:mat[i][idx[v]]-=pr
            elif v in answers:rhs[i][answers.index(v)]+=pr
        trans.append(row)
    prob=solve(mat,rhs)
    cost=[zero.copy() for _ in names]
    for i,edges in enumerate(trans):
        for v,pr,c in edges:
            if v in idx:
                for a in range(nans):cost[i][a]+=pr*c*prob[idx[v]][a]
            elif v in answers:cost[i][answers.index(v)]+=pr*c
    return prob[idx[start]],solve(mat,cost)[idx[start]]


def combine(p, left, right):
    answers=p['answers'];n=len(answers);correct=answers.index(p['correct'])
    def one(method,profile):
        pr,cost=([F(*v) for v in row] for row in right[method['id']][profile])
        @lru_cache(None)
        def ballot(counts):
            leader=left[1][method['id']][','.join(map(str,counts))]
            if leader is not None:
                return tuple(F(i==leader) for i in range(n)),F(0),F(0)
            wins=[F(0)]*n;launches=F(1);conditional_mass=F(0)
            for i in range(n):
                if pr[i]==0:continue
                updated=list(counts);updated[i]+=1
                child,z,m=ballot(tuple(updated))
                launches+=pr[i]*z;conditional_mass+=pr[i]*m+cost[i]*child[correct]
                for j in range(n):wins[j]+=pr[i]*child[j]
            return tuple(wins),launches,conditional_mass
        return ballot((0,)*n)
    def ratio(v):return [v.numerator,v.denominator]
    result=[]
    for method in p['methods']:
        prob=[F(0)]*n;launches=F(0);cost=F(0)
        for version,w in p['profiles'].items():
            prior=F(*left[0][version])
            x,a,b=one(method,version);launches+=prior*a;cost+=prior*b
            for i,v in enumerate(x):prob[i]+=prior*v
        row=dict(id=method['id'],prob=list(map(ratio,prob)),unresolved=ratio(1-sum(prob)),launches=ratio(launches),
                 cost_if_correct=ratio(cost/prob[correct]) if prob[correct] else None)
        result.append((-prob[correct],method['id'],row))
    return [r for _,_,r in sorted(result)]

from pathlib import Path
import json

