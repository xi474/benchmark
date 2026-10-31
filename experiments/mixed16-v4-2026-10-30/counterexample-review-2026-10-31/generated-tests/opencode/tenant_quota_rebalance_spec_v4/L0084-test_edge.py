import itertools

def compatible(a,b,cooldown):
    return a[1]+cooldown <= b[0] or b[1]+cooldown <= a[0]

def brute(intervals, cooldown):
    n=len(intervals)
    best_val=None; best_tuple=None
    for mask in range(1<<n):
        chosen=[intervals[i] for i in range(n) if mask>>i&1]
        ok=True
        for x,y in itertools.combinations(chosen,2):
            if not compatible((x[1],x[2]),(y[1],y[2]),cooldown): ok=False;break
        if not ok: continue
        val=sum(c[3] for c in chosen)
        tup=tuple(sorted(c[0] for c in chosen))
        if best_val is None or val>best_val or (val==best_val and tup<best_tuple):
            best_val=val; best_tuple=tup
    return best_val, best_tuple

# scenario: x value 5 id 'a', y value -1 id 'b', compatible
intervals=[('a',0,2,5),('b',4,6,-1)]
print("brute", brute(intervals,2))

# greedy with clamped extra
def maxw(items,cooldown):
    items=sorted(items,key=lambda x:(x[2],x[1],x[0]))
    n=len(items)
    if not n: return 0
    dp=[0]*n
    for i in range(n):
        best=0
        for j in range(i):
            if items[j][2]+cooldown<=items[i][1]:
                if dp[j]>best: best=dp[j]
        dp[i]=best+items[i][3]
    return max(dp)

def greedy(intervals,cooldown,clamp=True):
    W=max(0,maxw([(i[0],i[1],i[2],i[3]) for i in intervals],cooldown))
    items=sorted(intervals,key=lambda x:x[0])
    chosen=[]
    def val(chs): return sum(c[3] for c in chs)
    def comp(a,b): return a[1]+cooldown<=b[2] or b[1]+cooldown<=a[2]  # wrong indexing? a=(id,start,end,value)
    def comp2(a,b): return a[2]+cooldown<=b[1] or b[2]+cooldown<=a[1]
    for x in items:
        if val(chosen)==W: break
        if all(comp2(x,c) for c in chosen):
            cand=chosen+[x]
            allowed=[w for w in items if w not in cand and all(comp2(w,c) for c in cand)]
            base=val(cand)
            e=maxw([(w[0],w[1],w[2],w[3]) for w in allowed],cooldown)
            if clamp: e=max(0,e)
            if base+e==W: chosen=cand
    return val(chosen), tuple(sorted(c[0] for c in chosen))

print("greedy clamp", greedy(intervals,2,True))
print("greedy noclamp", greedy(intervals,2,False))
