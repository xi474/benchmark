from itertools import combinations


def measurements(q,selected):
    names=[h['id'] for h in q['habitats']];edges=[e for e in q['corridors'] if e['id'] in selected]
    coverage=0;flows=[]
    for season in q['seasons']:
        active=[e for e in edges if season['id'] in e['open']];source=season['source'];sink=season['sink'];reachable={source}
        changed=True
        while changed:
            changed=False
            for e in active:
                if (e['a'] in reachable)!=(e['b'] in reachable):reachable.update((e['a'],e['b']));changed=True
        coverage+=sum(h['quality'] for h in q['habitats'] if h['id'] in reachable)
        others=[k for k in names if k not in (source,sink)];best=0 if sink not in reachable else sum(e['capacity'] for e in active)
        if best:
            for size in range(len(others)+1):
                for extra in combinations(others,size):
                    cut={source,*extra};capacity=sum(e['capacity'] for e in active if (e['a'] in cut)!=(e['b'] in cut))
                    best=min(best,capacity)
        flows.append(dict(season=season['id'],max_flow=best))
    return dict(total_cost=sum(e['cost'] for e in edges),coverage=coverage,season_flows=flows)


def normalize(ident,value):
    return {**value,'selected':sorted(value['selected']),'season_flows':sorted(value['season_flows'],key=lambda x:x['season'])}


def check_value(task,component,actual,expected,request=None):
    try:
        if actual['status']!=expected['status']:return False
        if expected['status']=='infeasible':return normalize(task,actual)==normalize(task,expected)
        if not isinstance(request,dict):return False
        # Probe passes either the request or its containing payload, depending on entry point.
        q=request.get('request',request);selected=actual['selected']
        if len(selected)!=len(set(selected)) or not set(selected)<={e['id'] for e in q['corridors']}:return False
        measured=measurements(q,selected)
        if measured['total_cost']>q['budget']:return False
        demands={s['id']:s['demand'] for s in q['seasons']}
        if any(r['max_flow']<demands[r['season']] for r in measured['season_flows']):return False
        canonical=normalize(task,dict(status='feasible',selected=selected,**measured))
        if normalize(task,actual)!=canonical:return False
        return (actual['total_cost'],actual['coverage'])==(expected['total_cost'],expected['coverage'])
    except (TypeError,ValueError,KeyError,AttributeError,IndexError):return False
