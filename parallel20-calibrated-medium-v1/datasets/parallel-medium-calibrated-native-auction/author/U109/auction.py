from functools import lru_cache


def compile_request(q):
    item_index={x["id"]:i for i,x in enumerate(q["items"])};reserve={x["id"]:x["reserve"] for x in q["items"]}
    budgets={b["id"]:b["budget"] for b in q["bidders"]};groups={k:[] for k in budgets};ineligible=[]
    for bid in q["bids"]:
        if bid["value"]>budgets[bid["bidder"]] or bid["value"]<sum(reserve[k] for k in bid["items"]):ineligible.append(bid["id"]);continue
        mask=sum(1<<item_index[k] for k in bid["items"])
        groups[bid["bidder"]].append((bid["id"],mask,bid["value"],len(bid["items"])))
    return groups,sorted(ineligible)


def solve(q,independent=False,pick_one=False):
    if independent:
        from forward_oracle import solve as oracle
        return oracle(q)
    groups,ineligible=compile_request(q);names=sorted(groups);bid_counts={b["id"]:0 for b in q["bids"]}
    @lru_cache(None)
    def optimum(i,used):
        if i==len(names):return (0,0,0),1
        best,count=optimum(i+1,used)
        for ident,mask,value,covered in groups[names[i]]:
            if mask&used:continue
            tail,ways=optimum(i+1,used|mask);score=(tail[0]+value,tail[1]+covered,tail[2]-1)
            if score>best:best=score;count=0
            if score==best:count+=ways
        return best,count
    score,total=optimum(0,0);prefix={0:1}
    for i,name in enumerate(names):
        following={}
        for used,ways in prefix.items():
            current,_=optimum(i,used)
            for option in [None]+groups[name]:
                if option is None:mask=0;gain=(0,0,0)
                else:
                    ident,mask,value,covered=option
                    if mask&used:continue
                    gain=(value,covered,-1)
                tail,count=optimum(i+1,used|mask)
                if tuple(a+b for a,b in zip(gain,tail))!=current:continue
                following[used|mask]=following.get(used|mask,0)+ways
                if option is not None:bid_counts[ident]+=ways*count
        prefix=following
    assert sum(prefix.values())==total
    if pick_one:
        bid_counts={b["id"]:0 for b in q["bids"]};used=0
        for i,name in enumerate(names):
            current,_=optimum(i,used)
            for ident,mask,value,covered in groups[name]:
                if mask&used:continue
                tail,_=optimum(i+1,used|mask)
                if (tail[0]+value,tail[1]+covered,tail[2]-1)==current:
                    bid_counts[ident]=1;used|=mask;break
        total=1
    optimum.cache_clear()
    counterfactual={}
    for excluded in names:
        other=[name for name in names if name!=excluded]
        @lru_cache(None)
        def welfare(i,used):
            if i==len(other):return 0
            best=welfare(i+1,used)
            for ident,mask,value,covered in groups[other[i]]:
                if not mask&used:best=max(best,value+welfare(i+1,used|mask))
            return best
        counterfactual[excluded]=welfare(0,0);welfare.cache_clear()
    audit={}
    for name in names:
        winning=sum(bid_counts[ident] for ident,mask,v,c in groups[name]);payments=[]
        if winning<total:payments.append(0)
        payments.extend(counterfactual[name]-score[0]+value for ident,mask,value,c in groups[name] if bid_counts[ident])
        audit[name]=dict(winning_in=winning,payment_range=[min(payments),max(payments)])
    return dict(score=dict(welfare=score[0],allocated_items=score[1],winning_bids=-score[2]),
        optimal_allocations=total,selected_in=bid_counts,ineligible_bids=ineligible,
        counterfactual_welfare=counterfactual,bidders=audit)
