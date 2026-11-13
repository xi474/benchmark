from itertools import combinations


def analysis(q,independent=False):
    if independent:
        from bitflow import analyze
        return analyze(q)
    from source_liveness import analyze,interference
    blocks={b['id']:b for b in q['cfg']['blocks']};preds={k:[] for k in blocks}
    for k,b in blocks.items():
        for s in b['successors']:preds[s].append(k)
    live_in,live_out=analyze(blocks,preds)
    edges,forbidden=interference(blocks,q['spill_cost'],live_in,live_out,q['config']['call_clobbered'])
    return dict(live_in={k:sorted(v) for k,v in live_in.items()},live_out={k:sorted(v) for k,v in live_out.items()},
        interference=[list(e) for e in edges],call_forbidden=forbidden)


def solve(q,independent=False,greedy=False):
    a=analysis(q,independent);registers=q['config']['registers'];pins=q['config']['precolors'];reason=None
    if any(r in a['call_forbidden'].get(v,[]) for v,r in pins.items()):reason='PRECOLOR_CALL_CLOBBER'
    elif any(u in pins and v in pins and pins[u]==pins[v] for u,v in a['interference']):reason='PRECOLOR_INTERFERENCE'
    if reason:return dict(status='UNSAT_PRECOLOR',reason=reason,**a,min_spill=None,locations={},spills=[],edge_moves=[])
    big=1+sum(q['spill_cost'].values());values=[]
    for v,cost in q['spill_cost'].items():
        starts=[i for i,r in enumerate(registers) if r not in a['call_forbidden'].get(v,[]) and (v not in pins or pins[v]==r)]
        values.append(dict(id=v,width=1,starts=starts,spill_cost=big if v in pins else cost))
    graph=dict(values=values,conflicts=a['interference'])
    if independent:
        from color_mip import solve as color
        colored=color(graph)
    elif greedy:
        placed={v:registers.index(r) for v,r in pins.items()};adj={v:set() for v in q['spill_cost']}
        for u,v in a['interference']:adj[u].add(v);adj[v].add(u)
        for item in sorted((v for v in values if v['id'] not in pins),key=lambda v:(-v['spill_cost'],v['id'])):
            options=[r for r in item['starts'] if all(placed.get(n)!=r for n in adj[item['id']])]
            if options:placed[item['id']]=options[0]
        colored=dict(placement=placed)
    else:
        from physical_color import solve as color
        colored=color(graph)
    placed=colored['placement'];assert all(placed.get(v)==registers.index(r) for v,r in pins.items())
    locations={v:'reg:'+registers[placed[v]] if v in placed else 'spill:'+v for v in q['spill_cost']};spills=sorted(set(q['spill_cost'])-placed.keys())
    from semantic import edge_certificate
    return dict(status='ALLOCATED',reason=None,**a,min_spill=sum(q['spill_cost'][v] for v in spills),
        locations=locations,spills=spills,edge_moves=edge_certificate(q,locations))
