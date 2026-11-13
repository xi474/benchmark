"""Independent binary placement model: one choice per value, overlap rows per edge."""


def solve(q):
    import numpy as np
    from scipy.optimize import Bounds,LinearConstraint,milp
    from scipy.sparse import coo_matrix
    options=[];by_id={v["id"]:v for v in q["values"]}
    for value in q["values"]:
        for start in value["starts"]:options.append((value["id"],start,set(range(start,start+value["width"]))))
    if not options:return dict(min_spill=sum(v["spill_cost"] for v in q["values"]),placement={})
    rows=[]
    for value in q["values"]:rows.append([j for j,(name,s,slots) in enumerate(options) if name==value["id"]])
    for a,b in q["conflicts"]:
        for i,(x,s,left) in enumerate(options):
            if x!=a:continue
            for j,(y,t,right) in enumerate(options):
                if y==b and left.intersection(right):rows.append([i,j])
    rr=[];cc=[]
    for i,indices in enumerate(rows):
        for j in indices:rr.append(i);cc.append(j)
    a=coo_matrix((np.ones(len(rr)),(rr,cc)),shape=(len(rows),len(options))).tocsc()
    cost=np.array([-by_id[name]["spill_cost"] for name,s,slots in options],dtype=float)
    result=milp(c=cost,integrality=np.ones(len(options)),bounds=Bounds(0,1),constraints=LinearConstraint(a,0,1),options={"mip_rel_gap":0})
    assert result.success and result.mip_gap==0,result.message
    point=np.rint(result.x).astype(int);assert np.max(np.abs(point-result.x))<1e-6
    assert np.all(point>=0) and np.all(point<=1) and np.all(a@point<=1)
    placement={name:s for (name,s,slots),x in zip(options,point) if x}
    return dict(min_spill=sum(v["spill_cost"] for v in q["values"])-sum(by_id[k]["spill_cost"] for k in placement),placement=placement)
