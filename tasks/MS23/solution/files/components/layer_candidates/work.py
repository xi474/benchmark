from itertools import product
def compute(p):
    result=[]
    for q in p['snapshots']:
        ab,bc,ac=(q[k] for k in ('ab','bc','ac'));n=len(ab);blocked=set(map(tuple,q['forbidden']))
        layers=[]
        for b in range(n):
            opts=[]
            def fill(i,rr,cc,vec):
                if i==n*n:
                    if not any(rr) and not any(cc):
                        v=tuple(vec)
                        score=sum(x*((sorted([a,b,c])[1]==n-1)-(sorted([a,b,c])[1]==0))
                                  for (a,c),x in zip(product(range(n),repeat=2),v))
                        opts.append((v,score))
                    return
                a,c=divmod(i,n)
                for x in range(1+(0 if (a,b,c) in blocked else min(rr[a],cc[c],ac[a][c]))):
                    if (c==n-1 and x!=rr[a]) or (a==n-1 and x!=cc[c]):continue
                    rr[a]-=x;cc[c]-=x;fill(i+1,rr,cc,vec+[x]);rr[a]+=x;cc[c]+=x
            fill(0,[r[b] for r in ab],list(bc[b]),[]);layers.append(opts)
        result.append(layers)
    return result
