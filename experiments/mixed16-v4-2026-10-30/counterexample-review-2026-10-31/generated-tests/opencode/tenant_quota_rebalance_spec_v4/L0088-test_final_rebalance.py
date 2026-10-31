import random, itertools

def _max_weight(items, cooldown):
    items = sorted(items, key=lambda x: (x[2], x[1], x[0]))
    n = len(items)
    if n == 0:
        return 0
    dp = [0]*n
    for i in range(n):
        best = 0
        for j in range(i):
            if items[j][2] + cooldown <= items[i][1]:
                if dp[j] > best:
                    best = dp[j]
        dp[i] = best + items[i][3]
    return max(0, max(dp))

def solve(windows, cooldown):
    # windows: list of (id, start, end, value)
    W = _max_weight([(w[0],w[1],w[2],w[3]) for w in windows], cooldown)
    items = sorted(windows, key=lambda w: w[0])
    def comp(a,b): return a[2]+cooldown<=b[1] or b[2]+cooldown<=a[1]
    chosen=[]
    def val(chs): return sum(c[3] for c in chs)
    for x in items:
        if val(chosen)==W: break
        if all(comp(x,c) for c in chosen):
            cand=chosen+[x]
            allowed=[w for w in items if w not in cand and all(comp(w,c) for c in cand)]
            base=val(cand)
            extra=_max_weight([(w[0],w[1],w[2],w[3]) for w in allowed], cooldown)
            if base+extra==W:
                chosen=cand
    return val(chosen), tuple(sorted(c[0] for c in chosen))

def brute(intervals, cooldown):
    n=len(intervals)
    best_val=None; best_tuple=None
    for mask in range(1<<n):
        ch=[intervals[i] for i in range(n) if mask>>i&1]
        ok=True
        for x,y in itertools.combinations(ch,2):
            if not (x[2]+cooldown<=y[1] or y[2]+cooldown<=x[1]): ok=False;break
        if not ok: continue
        val=sum(c[3] for c in ch)
        tup=tuple(sorted(c[0] for c in ch))
        if best_val is None or val>best_val or (val==best_val and tup<best_tuple):
            best_val=val; best_tuple=tup
    return best_val, best_tuple

random.seed(1234)
fails=0
for t in range(200000):
    n=random.randint(0,12)
    cooldown=random.randint(0,4)
    intervals=[]
    for i in range(n):
        s=random.randint(0,14)
        e=random.randint(s+1,18)
        v=random.choice([-3,-2,-1,0,1,2,3,5])
        intervals.append((f'id{i:02d}',s,e,v))
    bv,bt=brute(intervals,cooldown)
    gv,gt=solve(intervals,cooldown)
    if (bv,bt)!=(gv,gt):
        fails+=1
        if fails<=10:
            print("FAIL",intervals,cooldown,"brute",bv,bt,"solve",gv,gt)
print("fails",fails)
