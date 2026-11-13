"""Weighted physical coloring using changing domains and exact upper bounds."""


def solve(q,independent=False,ignore_conflicts=False):
    if independent:
        from mip_oracle import solve as other
        return other(q)
    values=q["values"];n=len(values);index={v["id"]:i for i,v in enumerate(values)}
    neighbors=[0]*n
    if not ignore_conflicts:
        for a,b in q["conflicts"]:
            i,j=index[a],index[b];neighbors[i]|=1<<j;neighbors[j]|=1<<i
    options=[[(s,((1<<v["width"])-1)<<s) for s in v["starts"]] for v in values]
    weights=[v["spill_cost"] for v in values];best=0;answer={}
    def search(remaining,blocked,saved,placed):
        nonlocal best,answer
        if not remaining:
            if saved>best:best=saved;answer=dict(placed)
            return
        active=[i for i in range(n) if remaining>>i&1]
        domains={i:[(s,m) for s,m in options[i] if not m&blocked[i]] for i in active}
        upper=saved+sum(weights[i] for i in active if domains[i])
        if upper<=best:return
        v=min(active,key=lambda i:(len(domains[i]),-(neighbors[i]&remaining).bit_count(),-weights[i]))
        following=remaining^(1<<v)
        def impact(item):
            s,mask=item
            return sum(sum(bool(mask&m) for x,m in domains[j]) for j in active if neighbors[v]>>j&1)
        for start,mask in sorted(domains[v],key=impact):
            revised=list(blocked);adjacent=neighbors[v]&following
            while adjacent:
                bit=adjacent&-adjacent;adjacent^=bit;revised[bit.bit_length()-1]|=mask
            placed[values[v]["id"]]=start
            search(following,tuple(revised),saved+weights[v],placed)
            del placed[values[v]["id"]]
        search(following,blocked,saved,placed)
    search((1<<n)-1,(0,)*n,0,{})
    return dict(min_spill=sum(weights)-best,placement=answer)
