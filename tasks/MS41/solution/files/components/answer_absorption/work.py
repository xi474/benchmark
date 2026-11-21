from fractions import Fraction as F
def solve(matrix, values):
    a=[left.copy()+right.copy() for left,right in zip(matrix,values)]
    n=len(a)
    for k in range(n):
        pivot=next(i for i in range(k,n) if a[i][k])
        a[k],a[pivot]=a[pivot],a[k]
        lead=a[k][k];a[k]=[x/lead for x in a[k]]
        for i in range(n):
            if i!=k and a[i][k]:
                multiple=a[i][k];a[i]=[x-multiple*y for x,y in zip(a[i],a[k])]
    return [r[n:] for r in a]


def single(graph,start,answers):
    nans=len(answers);alive=set(answers)
    while True:
        grown=alive|{s for s,edges in graph.items() if any(v in alive for v,_,_ in edges)}
        if grown==alive:break
        alive=grown
    names=sorted(alive-set(answers));idx={s:i for i,s in enumerate(names)}
    n=len(names);zero=[F(0)]*nans
    if start not in idx:return zero,zero
    mat=[[F(i==j) for j in range(n)] for i in range(n)]
    rhs=[zero.copy() for _ in names]
    trans=[]
    for i,s in enumerate(names):
        total=sum(w for _,w,_ in graph[s]);row=[]
        for v,w,c in graph[s]:
            pr=F(w,total);row.append((v,pr,c))
            if v in idx:mat[i][idx[v]]-=pr
            elif v in answers:rhs[i][answers.index(v)]+=pr
        trans.append(row)
    prob=solve(mat,rhs)
    cost=[zero.copy() for _ in names]
    for i,edges in enumerate(trans):
        for v,pr,c in edges:
            if v in idx:
                for a in range(nans):cost[i][a]+=pr*c*prob[idx[v]][a]
            elif v in answers:cost[i][answers.index(v)]+=pr*c
    return prob[idx[start]],solve(mat,cost)[idx[start]]
def compute(p):
 def fractions(v):return [[x.numerator,x.denominator] for x in v]
 return {m['id']:{k:[fractions(v) for v in single(m['graphs'][k],m['start'],p['answers'])] for k in p['profiles']} for m in p['methods']}
