from public_semantic import check_ready,normalize


def check_value(task,component,actual,expected,request=None):
    try:
        q=request.get('request',request)
        if actual['status']!=expected['status']:return False
        if expected['status']=='ready':return check_ready(actual,expected,q)
        conflict=actual['minimal_root_conflict']
        if len(set(conflict))!=len(conflict) or len(conflict)!=len(expected['minimal_root_conflict']):return False
        roots={r['package']:r for r in q['config']['roots']}
        if not set(conflict)<=set(roots):return False
        from resolver import feasible
        if feasible(q,[roots[k] for k in conflict]):return False
        return normalize(task,{**actual,'minimal_root_conflict':expected['minimal_root_conflict']})==normalize(task,expected)
    except (TypeError,ValueError,KeyError,AttributeError):return False
