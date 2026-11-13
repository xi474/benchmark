def solve(q,a):
    import numpy as np
    from scipy.optimize import milp,Bounds,LinearConstraint
    from affinity_color import terms
    variables=list(q['spill_cost']);regs=q['config']['registers'];pins=q['config']['precolors'];options=[]
    for v in variables:
        for r in regs:
            if r not in a['call_forbidden'].get(v,[]) and (v not in pins or pins[v]==r):options.append((v,r))
    index={v:i for i,v in enumerate(options)};affinity=terms(q);z=[]
    for (u,v),weight in affinity.items():
        for r in regs:
            if (u,r) in index and (v,r) in index:z.append((u,v,r,weight))
    n=len(options)+len(z);rows=[];lower=[];upper=[]
    def add(row,lo,hi):rows.append(row);lower.append(lo);upper.append(hi)
    for v in variables:add({i:1 for i,(u,r) in enumerate(options) if u==v},int(v in pins),1)
    for u,v in a['interference']:
        for r in regs:
            if (u,r) in index and (v,r) in index:add({index[u,r]:1,index[v,r]:1},0,1)
    for j,(u,v,r,w) in enumerate(z,len(options)):
        x,y=index[u,r],index[v,r];add({j:1,x:-1},-np.inf,0);add({j:1,y:-1},-np.inf,0);add({j:1,x:-1,y:-1},-1,np.inf)
    scale=sum(affinity.values())+1;cost=np.array([-q['spill_cost'][v]*scale for v,r in options]+[-w for u,v,r,w in z],dtype=float)
    matrix=np.zeros((len(rows),n))
    for i,row in enumerate(rows):
        for j,c in row.items():matrix[i,j]=c
    if not n:return {v:'spill:'+v for v in variables}
    result=milp(cost,integrality=np.ones(n),bounds=Bounds(0,1),constraints=LinearConstraint(matrix,lower,upper),options={'mip_rel_gap':0})
    assert result.success and result.mip_gap==0,result.message
    placed={v:r for (v,r),x in zip(options,result.x) if x>.5}
    return {v:'reg:'+placed[v] if v in placed else 'spill:'+v for v in variables}
