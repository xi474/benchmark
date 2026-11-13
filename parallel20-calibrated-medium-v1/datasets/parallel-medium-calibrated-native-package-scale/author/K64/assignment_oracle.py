from itertools import combinations,product
from public_semantic import describe


def grouping(q):
    groups=[{p['package']} for p in q['catalog']]
    enabled=set(q['config']['features'])
    for p in q['catalog']:
        for v in p['versions']:
            for d in v['deps']:
                if d['feature'] is not None and d['feature'] not in enabled:continue
                touching=[g for g in groups if p['package'] in g or d['package'] in g]
                union=set().union(*touching);groups=[g for g in groups if g not in touching]+[union]
    return groups


def assignments(q,group,roots,first_only=False):
    packages=[p for p in q['catalog'] if p['package'] in group];count=0;best=None;choice=None
    local=dict(config={**q['config'],'roots':[r for r in roots if r['package'] in group],
        'prior':{k:v for k,v in q['config']['prior'].items() if k in group}},catalog=packages)
    for values in product(*([None]+[v['version'] for v in p['versions']] for p in packages)):
        selection={p['package']:v for p,v in zip(packages,values) if v is not None}
        try:report=describe(local,selection)
        except ValueError:continue
        count+=1;score=(report['score']['changes'],-report['score']['freshness'])
        if best is None or score<best:best=score;choice=selection
        if first_only:return count,choice
    return count,choice


def solve(q):
    groups=grouping(q);roots=q['config']['roots'];count=1;selected={};blocked=[]
    for g in groups:
        ways,choice=assignments(q,g,roots)
        if not ways:blocked.append(g)
        else:count*=ways;selected.update(choice)
    if not blocked:return dict(status='ready',**describe(q,selected),feasible_count=count,minimal_root_conflict=[])
    candidates=[]
    for g in blocked:
        local_roots=[r for r in roots if r['package'] in g]
        for size in range(1,len(local_roots)+1):
            failed=[sorted(r['package'] for r in subset) for subset in combinations(local_roots,size) if not assignments(q,g,subset,True)[0]]
            if failed:candidates+=failed;break
    return dict(status='blocked',selected=[],active_dependencies=[],prior_deltas=[],score=None,feasible_count=0,
        minimal_root_conflict=min(candidates,key=lambda r:(len(r),r)))
