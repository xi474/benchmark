"""Shared calibration choices, all-installation feasibility, then range recertification."""
from itertools import groupby,product
import lattice


def eligible_settings(q,board):
    valid=[]
    for setting in board["settings"]:
        consistent=True
        for ref in q["calibrations"]:
            if ref["board"]!=board["id"]:continue
            channel=setting["channels"][ref["channel"]]
            value=channel["offset"]+sum(a*ref["displacements"][k] for k,a in channel["coefficients"].items())
            if not ref["raw"][0]<=value<=ref["raw"][1]:consistent=False;break
        if consistent:valid.append(setting)
    return valid


def physical_problem(q,settings,gauges):
    selected={board["id"]:setting for board,setting in zip(q["boards"],settings)}
    setups=[]
    for setup in q["setups"]:
        extra=list(setup["constraints"])
        for reading in setup["readings"]:
            channel=selected[reading["board"]]["channels"][reading["channel"]]
            extra.append({"coefficients":channel["coefficients"],"min":reading["raw"][0]-channel["offset"],
                          "max":reading["raw"][1]-channel["offset"]})
        setups.append({"id":setup["id"],"extra":extra})
    return {"bounds":q["bounds"],"measurements":q["physical_constraints"],"setups":setups,"gauges":gauges}


def solve(q,independent=False,local_cheapest=False):
    if independent:
        from calibrated_oracle import solve as oracle
        return oracle(q)
    candidates=product(*(eligible_settings(q,board) for board in q["boards"]))
    ranked=sorted(((sum(s["penalty"] for s in settings),settings) for settings in candidates),key=lambda x:x[0])
    best=None;survivors=[]
    for price,wave in groupby(ranked,key=lambda x:x[0]):
        for _,settings in wave:
            result=lattice.solve(physical_problem(q,settings,[]))
            if all(s["feasible"] for s in result["setups"].values()):survivors.append(settings)
            if local_cheapest:break
        if survivors:best=price;break
        if local_cheapest:break
    if best is None:return {"minimum_cost":None,"setting_options":{},"ranges":{}}
    ranges={s["id"]:{} for s in q["setups"]}
    options={b["id"]:set() for b in q["boards"]}
    for settings in survivors:
        for board,setting in zip(q["boards"],settings):options[board["id"]].add(setting["id"])
        result=lattice.solve(physical_problem(q,settings,q["gauges"]))
        for setup,item in result["setups"].items():
            for gauge,pair in item["ranges"].items():
                old=ranges[setup].get(gauge,pair)
                ranges[setup][gauge]=[min(old[0],pair[0]),max(old[1],pair[1])]
    return {"minimum_cost":best,"setting_options":{k:sorted(v) for k,v in options.items()},"ranges":ranges}
