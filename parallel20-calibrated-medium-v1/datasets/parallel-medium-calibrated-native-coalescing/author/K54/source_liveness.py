def analyze(blocks,preds):
    names=sorted(blocks);use={};defined={};phi_defs={}
    for name in names:
        b=blocks[name];phis={p['def'] for p in b['phis']};phi_defs[name]=phis;seen=set(phis);needed=set()
        for ins in b['instructions']:
            needed.update(x for x in ins['uses'] if x not in seen)
            if ins['def'] is not None:seen.add(ins['def'])
        use[name]=needed;defined[name]=seen
    live_in={x:set() for x in names};live_out={x:set() for x in names}
    while True:
        changed=False
        for name in reversed(names):
            out=set()
            for succ in blocks[name]['successors']:
                out.update(live_in[succ]-phi_defs[succ])
                for p in blocks[succ]['phis']:out.add(p['inputs'][name])
            inside=use[name]|(out-defined[name])
            if out!=live_out[name] or inside!=live_in[name]:live_out[name]=out;live_in[name]=inside;changed=True
        if not changed:break
    return live_in,live_out


def interference(blocks,allvars,live_in,live_out,clobbered):
    edges=set();forbidden={x:set() for x in allvars}
    def pair(a,b):
        if a!=b:edges.add(tuple(sorted((a,b))))
    def clique(vals):
        vals=sorted(vals)
        for i,a in enumerate(vals):
            for b in vals[i+1:]:pair(a,b)
    for name,b in blocks.items():
        live=set(live_out[name]);clique(live)
        for ins in reversed(b['instructions']):
            after=set(live);d=ins['def']
            if ins['call']:
                for v in after-({d} if d is not None else set()):forbidden[v].update(clobbered)
            if d is not None:
                for v in live:pair(d,v)
                live.discard(d)
            live.update(ins['uses']);clique(live)
        clique(live)
        clique(live_in[name])
    return sorted(edges),{v:sorted(r) for v,r in sorted(forbidden.items()) if r}
