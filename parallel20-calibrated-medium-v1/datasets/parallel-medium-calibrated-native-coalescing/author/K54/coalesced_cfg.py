from cfg_allocate import analysis


def solve(q,independent=False,ignore_copies=False):
    a=analysis(q,independent);pins=q['config']['precolors'];reason=None
    if any(r in a['call_forbidden'].get(v,[]) for v,r in pins.items()):reason='PRECOLOR_CALL_CLOBBER'
    elif any(u in pins and v in pins and pins[u]==pins[v] for u,v in a['interference']):reason='PRECOLOR_INTERFERENCE'
    if reason:return dict(status='UNSAT_PRECOLOR',reason=reason,**a,min_spill=None,copy_cost=None,locations={},spills=[],edge_moves=[])
    if ignore_copies:
        from cfg_allocate import solve as previous
        locations=previous(q)['locations']
    elif independent:
        from affinity_mip import solve as color
        locations=color(q,a)
    else:
        from affinity_color import solve as color
        locations=color(q,a)
    from semantic import edge_certificate
    from affinity_color import copy_cost
    spills=sorted(v for v,loc in locations.items() if loc=='spill:'+v)
    return dict(status='ALLOCATED',reason=None,**a,min_spill=sum(q['spill_cost'][v] for v in spills),copy_cost=copy_cost(q,locations),locations=locations,spills=spills,edge_moves=edge_certificate(q,locations))
