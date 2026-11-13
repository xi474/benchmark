from graphlib import TopologicalSorter,CycleError


def edge_certificate(q,locations):
    blocks={b['id']:b for b in q['cfg']['blocks']};rows=[]
    for pred,b in blocks.items():
        for succ in b['successors']:
            moves=[];dependencies={}
            for phi in blocks[succ]['phis']:
                source=phi['inputs'][pred];dest=phi['def'];left,right=locations[source],locations[dest]
                if left==right:continue
                moves.append(dict(definition=dest,source=source,from_location=left,to_location=right));dependencies.setdefault(left,set());dependencies.setdefault(right,set()).add(left)
            try:list(TopologicalSorter(dependencies).static_order());cycle=False
            except CycleError:cycle=True
            rows.append(dict(pred=pred,succ=succ,moves=moves,cycle=cycle))
    return rows


def normalize(ident,v):
    return {**v,'live_in':{k:sorted(set(x)) for k,x in v['live_in'].items()},'live_out':{k:sorted(set(x)) for k,x in v['live_out'].items()},
        'interference':sorted({tuple(sorted(e)) for e in v['interference']}),
        'call_forbidden':{k:sorted(set(x)) for k,x in v['call_forbidden'].items() if x},'spills':sorted(set(v['spills'])),
        'edge_moves':sorted(({**row,'moves':sorted(row['moves'],key=lambda m:(m['definition'],m['source']))} for row in v['edge_moves']),key=lambda r:(r['pred'],r['succ']))}


def check_value(task,component,actual,expected,request=None):
    try:
        a=normalize(task,actual);e=normalize(task,expected);q=request.get('request',request)
        if set(a)!=set(e) or any(a[k]!=e[k] for k in ['status','reason','live_in','live_out','interference','call_forbidden','min_spill','copy_cost']):return False
        if e['status']=='UNSAT_PRECOLOR':return a==e
        loc=a['locations'];variables=set(q['spill_cost']);regs=q['config']['registers']
        if set(loc)!=variables:return False
        spilled={v for v in variables if loc[v]=='spill:'+v}
        if set(a['spills'])!=spilled or sum(q['spill_cost'][v] for v in spilled)!=a['min_spill']:return False
        if any(v not in spilled and loc[v] not in ['reg:'+r for r in regs] for v in variables):return False
        if any(loc[v]!='reg:'+r for v,r in q['config']['precolors'].items()):return False
        if any(loc[v]=='reg:'+r for v,rs in e['call_forbidden'].items() for r in rs):return False
        if any(u not in spilled and v not in spilled and loc[u]==loc[v] for u,v in e['interference']):return False
        rows=edge_certificate(q,loc);measured=normalize(task,{**actual,'edge_moves':rows})
        return a['edge_moves']==measured['edge_moves'] and a['copy_cost']==sum(next(e['frequency'] for e in q['edge_frequency'] if (e['pred'],e['succ'])==(row['pred'],row['succ']))*len(row['moves']) for row in rows)
    except (TypeError,ValueError,KeyError,AttributeError,IndexError):return False
