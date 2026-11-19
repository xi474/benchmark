def fits(version,low,high):
    value=tuple(version)
    return (low is None or tuple(low)<=value) and (high is None or value<tuple(high))


def active(q,dep):return dep['feature'] is None or dep['feature'] in q['config']['features']


def describe(q,selection):
    catalog={p['package']:{tuple(v['version']):v for v in p['versions']} for p in q['catalog']};selected={k:tuple(v) for k,v in selection.items()}
    if any(k not in catalog or v not in catalog[k] for k,v in selected.items()):raise ValueError('unoffered')
    closure={r['package'] for r in q['config']['roots']}
    if any(r['package'] not in selected or not fits(selected[r['package']],r['min'],r['max']) for r in q['config']['roots']):raise ValueError('root')
    changed=True
    while changed:
        changed=False
        for package in list(closure):
            if package not in selected:raise ValueError('required')
            for d in catalog[package][selected[package]]['deps']:
                if active(q,d) and d['kind']=='required' and d['package'] not in closure:closure.add(d['package']);changed=True
    if closure!=set(selected):raise ValueError('extraneous')
    edges=[]
    for package,version in selected.items():
        for d in catalog[package][version]['deps']:
            if not active(q,d):continue
            target=d['package']
            if target not in selected or not fits(selected[target],d['min'],d['max']):raise ValueError('dependency')
            edges.append(dict(source=package,target=target,kind=d['kind'],feature=d['feature']))
    prior={k:tuple(v) for k,v in q['config']['prior'].items()};changed=[k for k in prior.keys()|selected.keys() if prior.get(k)!=selected.get(k)]
    deltas=[dict(package=k,prior=list(prior[k]) if k in prior else None,selected=list(selected[k]) if k in selected else None) for k in sorted(changed)]
    freshness=sum(100*v[0]+10*v[1]+v[2] for v in selected.values())
    return dict(selected=[dict(package=k,version=list(v)) for k,v in sorted(selected.items())],active_dependencies=edges,
        prior_deltas=deltas,score=dict(changes=len(changed),freshness=freshness))


def normalize(ident,v):
    return {**v,'selected':sorted(v['selected'],key=lambda r:r['package']),
        'active_dependencies':sorted(v['active_dependencies'],key=lambda r:(r['source'],r['target'],r['kind'],r['feature'] or '')),
        'prior_deltas':sorted(v['prior_deltas'],key=lambda r:r['package']),'minimal_root_conflict':sorted(v['minimal_root_conflict'])}


def check_ready(actual,expected,q):
    if set(actual)!={'status','selected','active_dependencies','prior_deltas','score','feasible_count','minimal_root_conflict'}:return False
    selected={r['package']:r['version'] for r in actual['selected']}
    if len(selected)!=len(actual['selected']):return False
    measured=dict(status='ready',**describe(q,selected),feasible_count=expected['feasible_count'],minimal_root_conflict=[])
    return normalize('',actual)==normalize('',measured) and measured['score']==expected['score']


def check_value(task,component,actual,expected,request=None):
    try:
        q=request.get('request',request)
        if actual['status']!=expected['status']:return False
        if expected['status']=='ready':return check_ready(actual,expected,q)
        # Official public input is feasible. No hidden conflict search or optimizer is distributed here.
        return normalize(task,actual)==normalize(task,expected)
    except (TypeError,ValueError,KeyError,AttributeError):return False
