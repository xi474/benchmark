import random, itertools

def compatible(a,b,cooldown):
    # a,b = (start,end)
    return a[1]+cooldown <= b[0] or b[1]+cooldown <= a[0]

def brute(intervals, cooldown):
    # intervals: list of (id, start, end, value)
    n=len(intervals)
    best_val=None; best_tuple=None
    for mask in range(1<<n):
        chosen=[intervals[i] for i in range(n) if mask>>i&1]
        ok=True
        for x,y in itertools.combinations(chosen,2):
            if not compatible((x[1],x[2]),(y[1],y[2]),cooldown):
                ok=False;break
        if not ok: continue
        val=sum(c[3] for c in chosen)
        tup=tuple(sorted(c[0] for c in chosen))
        if best_val is None or val>best_val or (val==best_val and tup<best_tuple):
            best_val=val; best_tuple=tup
    return best_val, best_tuple

def dp_full(intervals, cooldown):
    # sort by end
    items=sorted(intervals,key=lambda x:(x[2],x[1],x[0]))
    n=len(items)
    # precompute p
    p=[-1]*n
    for i in range(n):
        for j in range(i):
            if items[j][2]+cooldown<=items[i][1]:
                p[i]=j
        # since sorted by end, p[i] should be largest compatible
    # but above loop gives largest j with end_j+cooldown<=start_i
    dp=[None]*n
    for i in range(n):
        skip=dp[i-1] if i-1>=0 else (0,())
        if p[i]>=0:
            pv,pt=dp[p[i]]
        else:
            pv,pt=0,()
        tv=pv+items[i][3]
        tt=tuple(sorted(pt+(items[i][0],)))
        take=(tv,tt)
        # better: higher val, tie lex smaller tuple
        if skip[0]>take[0] or (skip[0]==take[0] and skip[1]<take[1]):
            dp[i]=skip
        else:
            dp[i]=take
    return dp[n-1] if n else (0,())

def greedy_stop(intervals, cooldown):
    items=sorted(intervals,key=lambda x:x[0])
    n=len(items)
    # max weight subset
    W=dp_full(intervals,cooldown)[0]
    def maxw_subset(sub):
        if not sub: return 0
        return dp_full(sub,cooldown)[0]
    chosen=[]
    def comp(a,b):
        return compatible((a[1],a[2]),(b[1],b[2]),cooldown)
    for x in items:
        if sum(c[3] for c in chosen)==W:
            break
        if all(comp(x,c) for c in chosen):
            cand=chosen+[x]
            # can_extend(cand)
            allowed=[w for w in items if w not in cand and all(comp(w,c) for c in cand)]
            base=sum(c[3] for c in cand)
            extra=maxw_subset(allowed)
            if base+extra==W:
                chosen=cand
    val=sum(c[3] for c in chosen)
    tup=tuple(sorted(c[0] for c in chosen))
    return val,tup

random.seed(0)
fails_dp=0; fails_greedy=0
for t in range(20000):
    n=random.randint(0,10)
    cooldown=random.randint(0,3)
    ids=[f'id{i}' for i in range(n)]
    intervals=[]
    for i in range(n):
        s=random.randint(0,8)
        e=random.randint(s+1,12)
        v=random.choice([-2,-1,0,1,2,3])
        intervals.append((ids[i],s,e,v))
    bv,bt=brute(intervals,cooldown)
    dv,dt=dp_full(intervals,cooldown)
    gv,gt=greedy_stop(intervals,cooldown)
    if (bv,bt)!=(dv,dt):
        fails_dp+=1
        if fails_dp<=5:
            print("DP FAIL",intervals,cooldown,"brute",bv,bt,"dp",dv,dt)
    if (bv,bt)!=(gv,gt):
        fails_greedy+=1
        if fails_greedy<=5:
            print("GREEDY FAIL",intervals,cooldown,"brute",bv,bt,"greedy",gv,gt)
print("dp fails",fails_dp,"greedy fails",fails_greedy)
