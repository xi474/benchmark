"""Independent forward configuration DP and forced-bid reoptimization."""


def solve(q):
    goods=sorted(x["id"] for x in q["items"]);reserves={x["id"]:x["reserve"] for x in q["items"]}
    budgets={x["id"]:x["budget"] for x in q["bidders"]};by_owner={k:[] for k in budgets};valid={};bad=[]
    for bid in q["bids"]:
        if not sum(reserves[k] for k in bid["items"])<=bid["value"]<=budgets[bid["bidder"]]:bad.append(bid["id"]);continue
        entry=(sum(2**goods.index(k) for k in bid["items"]),bid["value"],len(bid["items"]),bid["id"])
        by_owner[bid["bidder"]].append(entry);valid[bid["id"]]=bid
    def optimize(exclude=None,force=None):
        used=0;base=(0,0,0);skip=exclude
        if force is not None:
            bid=valid[force];used=sum(2**goods.index(k) for k in bid["items"]);base=(bid["value"],len(bid["items"]),-1);skip=bid["bidder"]
        states={used:(base,1)}
        for owner in sorted(by_owner,reverse=True):
            if owner==skip:continue
            revised={}
            for occupied,(score,count) in states.items():
                for mask,value,coverage,ident in [(0,0,0,None)]+by_owner[owner]:
                    if occupied&mask:continue
                    target=occupied|mask;candidate=(score[0]+value,score[1]+coverage,score[2]-int(ident is not None))
                    old=revised.get(target)
                    if old is None or candidate>old[0]:revised[target]=(candidate,count)
                    elif candidate==old[0]:revised[target]=(candidate,old[1]+count)
            states=revised
        best=max(score for score,count in states.values());count=sum(count for score,count in states.values() if score==best)
        return best,count
    best,total=optimize();support={b["id"]:0 for b in q["bids"]}
    for ident in valid:
        conditional,count=optimize(force=ident)
        if conditional==best:support[ident]=count
    counter={k:optimize(exclude=k)[0][0] for k in by_owner};audit={}
    for owner,entries in by_owner.items():
        winning=sum(support[ident] for mask,v,c,ident in entries);payments=[0] if winning<total else []
        payments.extend(counter[owner]-best[0]+value for mask,value,c,ident in entries if support[ident])
        audit[owner]=dict(winning_in=winning,payment_range=[min(payments),max(payments)])
    return dict(score=dict(welfare=best[0],allocated_items=best[1],winning_bids=-best[2]),optimal_allocations=total,
                selected_in=support,ineligible_bids=sorted(bad),counterfactual_welfare=counter,bidders=audit)
