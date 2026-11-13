"""Independent joint investment/flow model; exact cut certificates check its output."""
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from semantic import measurements


def solve(q):
    names=[h['id'] for h in q['habitats']];index={k:i for i,k in enumerate(names)};edges=q['corridors'];m=len(edges);n=len(names)
    if not m:return dict(status='infeasible',selected=[],total_cost=None,coverage=None,season_flows=[])
    rows=[];lower=[];upper=[];lo=[0.]*m;hi=[1.]*m;integer=[1]*m
    def var(lb,ub,integral=0):
        at=len(lo);lo.append(lb);hi.append(ub);integer.append(integral);return at
    def rule(coeff,a,b):rows.append(coeff);lower.append(a);upper.append(b)
    for season in q['seasons']:
        arcs=[]
        for i,e in enumerate(edges):
            if season['id'] not in e['open']:continue
            f=var(-e['capacity'],e['capacity']);arcs.append((i,f));rule({f:1,i:-e['capacity']},-np.inf,0);rule({f:-1,i:-e['capacity']},-np.inf,0)
        for v,name in enumerate(names):
            balance={f:(int(e['a']==name)-int(e['b']==name)) for i,f in arcs for e in [edges[i]] if name in (e['a'],e['b'])}
            need=season['demand']*(int(name==season['source'])-int(name==season['sink']));rule(balance,need,need)
    costs={i:e['cost'] for i,e in enumerate(edges)};rule(costs,-np.inf,q['budget'])
    def optimize(objective):
        mat=np.zeros((len(rows),len(lo)))
        for j,row in enumerate(rows):
            for k,v in row.items():mat[j,k]=v
        c=np.zeros(len(lo))
        for k,v in objective.items():c[k]=v
        return milp(c,integrality=np.array(integer),bounds=Bounds(lo,hi),constraints=LinearConstraint(mat,lower,upper),options={'time_limit':60,'mip_rel_gap':0})
    first=optimize(costs)
    if first.status==2:return dict(status='infeasible',selected=[],total_cost=None,coverage=None,season_flows=[])
    assert first.success,first.message
    optimum=round(first.fun);rule(costs,optimum,optimum);coverage={}
    for season in q['seasons']:
        source=season['source'];reached={}
        for h in q['habitats']:
            y=var(1 if h['id']==source else 0,1,1);reached[h['id']]=y;coverage[y]=-h['quality']
        arcs=[]
        for i,e in enumerate(edges):
            if season['id'] not in e['open']:continue
            f=var(-(n-1),n-1);arcs.append((i,f));rule({f:1,i:-(n-1)},-np.inf,0);rule({f:-1,i:-(n-1)},-np.inf,0)
        for name in names:
            balance={f:(int(e['a']==name)-int(e['b']==name)) for i,f in arcs for e in [edges[i]] if name in (e['a'],e['b'])}
            if name==source:
                balance.update({reached[k]:-1 for k in names if k!=source})
            else:balance[reached[name]]=1
            rule(balance,0,0)
    second=optimize(coverage);assert second.success,second.message
    selected=[e['id'] for i,e in enumerate(edges) if second.x[i]>.5]
    actual=measurements(q,selected);assert actual['total_cost']==optimum and actual['coverage']==round(-second.fun)
    return dict(status='feasible',selected=selected,**actual)
