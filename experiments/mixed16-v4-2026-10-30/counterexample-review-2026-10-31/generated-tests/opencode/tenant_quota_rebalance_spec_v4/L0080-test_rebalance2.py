import random, itertools
from test_rebalance import compatible, brute, greedy_stop

def gen_ids(n):
    names=['w0','alt1','a9','b2','x','y','m10','n2','k1','z','alpha','beta','g1','g10','c']
    return random.sample(names,n) if n<=len(names) else [f'id{i}' for i in range(n)]

random.seed(42)
fails=0
for t in range(100000):
    n=random.randint(0,12)
    cooldown=random.randint(0,5)
    ids=gen_ids(n)
    intervals=[]
    for i in range(n):
        s=random.randint(0,15)
        e=random.randint(s+1,20)
        v=random.choice([-3,-1,0,1,2,4,7])
        intervals.append((ids[i],s,e,v))
    bv,bt=brute(intervals,cooldown)
    gv,gt=greedy_stop(intervals,cooldown)
    if (bv,bt)!=(gv,gt):
        fails+=1
        if fails<=10:
            print("FAIL",intervals,cooldown,"brute",bv,bt,"greedy",gv,gt)
print("greedy fails",fails)
