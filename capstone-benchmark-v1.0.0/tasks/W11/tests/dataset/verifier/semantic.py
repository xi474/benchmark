import json
from fractions import Fraction
from graphlib import TopologicalSorter


def normalize(ident,value,field=""):
    if isinstance(value,dict):
        return {k:normalize(ident,v,k) for k,v in value.items()}
    if isinstance(value,list):
        if (ident,field) in {("W10","forced_changes"),("W14","possible_faults")}:
            return sorted(value)
        if ident=="W10" and field=="loss":
            if len(value)!=2 or any(type(x) is not int for x in value) or value[1]<=0:raise ValueError
            q=Fraction(*value);return [q.numerator,q.denominator]
    return value


def check_value(ident,name,actual,wanted,context=None):
    try:
        if ident!="W13":
            return json.dumps(normalize(ident,actual),sort_keys=True)==json.dumps(normalize(ident,wanted),sort_keys=True)
        d=context.get("request",context);events={r["id"]:r for r in d["events"]}
        if set(actual)!={"schedule"} or not isinstance(actual["schedule"],dict):return False
        assignment=actual["schedule"];parents={k:r["parents"] for k,r in events.items()};latest={}
        if any(k not in events or type(s) is not int or s not in events[k]["slots"] for k,s in assignment.items()):return False
        for k in TopologicalSorter(parents).static_order():
            lower=max((latest[p] for p in parents[k]),default=0)
            if k in assignment and assignment[k]<=lower:return False
            latest[k]=assignment.get(k,lower)
        return sum(events[k]["value"] for k in assignment)==sum(events[k]["value"] for k in wanted["schedule"])
    except (TypeError,KeyError,ValueError,ZeroDivisionError):
        return False
