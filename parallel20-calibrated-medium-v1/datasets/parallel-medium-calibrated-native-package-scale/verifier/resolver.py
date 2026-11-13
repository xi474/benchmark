from itertools import combinations
from public_semantic import active,fits,describe


def components(q):
    graph={p['package']:set() for p in q['catalog']}
    for p in q['catalog']:
        for v in p['versions']:
            for d in v['deps']:
                if active(q,d):graph[p['package']].add(d['package']);graph[d['package']].add(p['package'])
    seen=set();result=[]
    for start in graph:
        if start in seen:continue
        group={start};todo=[start];seen.add(start)
        for u in todo:
            for v in graph[u]:
                if v not in seen:seen.add(v);group.add(v);todo.append(v)
        result.append(group)
    return result


def select_component(q,names,roots,first_only=False,peer_pulls=False):
    catalog={p['package']:p['versions'] for p in q['catalog']};root_map={r['package']:r for r in roots if r['package'] in names}
    prior=q['config']['prior'];count=0;best=None;choice=None
    def walk(chosen,needed):
        nonlocal count,best,choice
        required=set(needed);constraints={k:[] for k in names}
        for k,r in root_map.items():constraints[k].append(r)
        for k,v in chosen.items():
            for d in v['deps']:
                if active(q,d):
                    constraints[d['package']].append(d)
                    if d['kind']=='required' or peer_pulls:required.add(d['package'])
        for k,v in chosen.items():
            if any(not fits(v['version'],d['min'],d['max']) for d in constraints[k]):return False
        pending=required-chosen.keys()
        if not pending:
            if any(active(q,d) and d['package'] not in chosen for v in chosen.values() for d in v['deps']):return False
            count+=1;changes=sum((prior.get(k)!=chosen[k]['version']) if k in chosen else k in prior for k in names)
            fresh=sum(100*v['version'][0]+10*v['version'][1]+v['version'][2] for v in chosen.values());score=(changes,-fresh)
            if best is None or score<best:best=score;choice={k:v['version'] for k,v in chosen.items()}
            return first_only
        domains={k:[v for v in catalog[k] if all(fits(v['version'],d['min'],d['max']) for d in constraints[k])] for k in pending}
        target=min(domains,key=lambda k:(len(domains[k]),k))
        for version in domains[target]:
            if walk({**chosen,target:version},required) and first_only:return True
        return False
    walk({},set(root_map))
    return count,choice


def feasible(q,roots):return all(select_component(q,g,roots,True)[0] for g in components(q))


def solve(q,independent=False,peer_pulls=False):
    if independent:
        from assignment_oracle import solve as other
        return other(q)
    roots=q['config']['roots'];groups=components(q);count=1;selected={};bad=[]
    for group in groups:
        ways,choice=select_component(q,group,roots,peer_pulls=peer_pulls)
        if not ways:bad.append(group)
        else:count*=ways;selected.update(choice)
    if bad:
        conflicts=[]
        for group in bad:
            candidates=sorted((r for r in roots if r['package'] in group),key=lambda r:r['package'])
            found=False
            for size in range(1,len(candidates)+1):
                for subset in combinations(candidates,size):
                    if not select_component(q,group,subset,True,peer_pulls=peer_pulls)[0]:
                        conflicts.append(sorted(r['package'] for r in subset));found=True;break
                if found:break
        conflict=min(conflicts,key=lambda r:(len(r),r))
        return dict(status='blocked',selected=[],active_dependencies=[],prior_deltas=[],score=None,feasible_count=0,minimal_root_conflict=conflict)
    return dict(status='ready',**describe(q,selected),feasible_count=count,minimal_root_conflict=[])
