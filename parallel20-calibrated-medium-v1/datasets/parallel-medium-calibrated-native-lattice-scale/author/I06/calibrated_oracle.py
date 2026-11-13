"""One joint integer model for calibration selectors and every assembly state."""


def solve(q):
    import numpy as np
    from scipy.optimize import Bounds,LinearConstraint,milp
    from scipy.sparse import coo_matrix
    variables={};lo=[];hi=[];penalties=[]
    for setup in q["setups"]:
        for k,(a,b) in q["bounds"].items():
            variables["x",setup["id"],k]=len(lo);lo.append(a);hi.append(b);penalties.append(0)
    for board in q["boards"]:
        for mode in board["settings"]:
            valid=True
            for ref in q["calibrations"]:
                if ref["board"]!=board["id"]:continue
                channel=mode["channels"][ref["channel"]]
                raw=channel["offset"]+sum(a*ref["displacements"][k] for k,a in channel["coefficients"].items())
                valid=valid and ref["raw"][0]<=raw<=ref["raw"][1]
            variables["z",board["id"],mode["id"]]=len(lo)
            lo.append(0);hi.append(int(valid));penalties.append(mode["penalty"])
    rows=[];lower=[];upper=[]
    def add(coeff,a,b):
        rows.append({variables[k]:v for k,v in coeff.items()});lower.append(a);upper.append(b)
    for board in q["boards"]:
        add({("z",board["id"],m["id"]):1 for m in board["settings"]},1,1)
    boards={b["id"]:b for b in q["boards"]}
    for setup in q["setups"]:
        sid=setup["id"]
        for row in q["physical_constraints"]+setup["constraints"]:
            add({("x",sid,k):a for k,a in row["coefficients"].items()},row["min"],row["max"])
        for reading in setup["readings"]:
            for mode in boards[reading["board"]]["settings"]:
                channel=mode["channels"][reading["channel"]]
                coefficients=channel["coefficients"]
                minimum=sum(a*(q["bounds"][k][0] if a>0 else q["bounds"][k][1]) for k,a in coefficients.items())
                maximum=sum(a*(q["bounds"][k][1] if a>0 else q["bounds"][k][0]) for k,a in coefficients.items())
                a=reading["raw"][0]-channel["offset"];b=reading["raw"][1]-channel["offset"]
                down=max(0,a-minimum);up=max(0,maximum-b)
                selector=("z",reading["board"],mode["id"])
                coeff={ ("x",sid,k):v for k,v in coefficients.items() }
                add({**coeff,selector:-down},a-down,float("inf"))
                add({**coeff,selector:up},-float("inf"),b+up)
    n=len(variables)
    def optimize(objective,extra=None):
        constraints=list(rows);low=list(lower);high=list(upper)
        if extra:
            for coeff,a,b in extra:constraints.append(coeff);low.append(a);high.append(b)
        rr=[];cc=[];vv=[]
        for i,row in enumerate(constraints):
            for j,value in row.items():rr.append(i);cc.append(j);vv.append(value)
        matrix=coo_matrix((vv,(rr,cc)),shape=(len(low),n)).tocsc()
        c=np.array([objective.get(j,0) for j in range(n)],dtype=float)
        result=milp(c=c,integrality=np.ones(n),bounds=Bounds(lo,hi),constraints=LinearConstraint(matrix,low,high),options={"mip_rel_gap":0})
        if result.status==2:return None
        assert result.success and result.mip_gap==0,result.message
        point=np.rint(result.x).astype(int)
        assert np.max(np.abs(point-result.x))<1e-6
        assert np.all(point>=np.array(lo)) and np.all(point<=np.array(hi))
        assert np.all(matrix@point>=np.array(low)-1e-6) and np.all(matrix@point<=np.array(high)+1e-6)
        return sum(objective.get(j,0)*int(point[j]) for j in range(n))
    cost={j:v for j,v in enumerate(penalties) if v}
    best=optimize(cost)
    if best is None:return {"minimum_cost":None,"setting_options":{},"ranges":{}}
    optimal=[(cost,best,best)]
    options={}
    for board in q["boards"]:
        options[board["id"]]=[]
        for mode in board["settings"]:
            j=variables["z",board["id"],mode["id"]]
            if optimize({},optimal+[({j:1},1,1)]) is not None:options[board["id"]].append(mode["id"])
        options[board["id"]].sort()
    ranges={}
    for setup in q["setups"]:
        ranges[setup["id"]]={}
        for gauge in q["gauges"]:
            objective={variables["x",setup["id"],k]:a for k,a in gauge["coefficients"].items()}
            minimum=optimize(objective,optimal)
            maximum=-optimize({k:-v for k,v in objective.items()},optimal)
            ranges[setup["id"]][gauge["id"]]=[gauge["base"]+minimum,gauge["base"]+maximum]
    return {"minimum_cost":best,"setting_options":options,"ranges":ranges}
