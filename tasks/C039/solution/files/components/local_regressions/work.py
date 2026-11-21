import itertools
def solve(a,b):
 a=[list(map(float,row))+[float(v)] for row,v in zip(a,b)];n=len(a)
 for i in range(n):
  k=max(range(i,n),key=lambda j:abs(a[j][i]));a[i],a[k]=a[k],a[i];v=a[i][i]
  for j in range(i,n+1):a[i][j]/=v
  for k in range(n):
   if k!=i:
    v=a[k][i]
    for j in range(i,n+1):a[k][j]-=v*a[i][j]
 return [a[i][-1] for i in range(n)]
def compute(p):
 names=p['nodes'];cov=p['covariance'];out=[]
 for b,name in enumerate(names):
  parents=sorted({names.index(a) for a,z in p['allowed'] if z==name and z!=p['root']})
  rows={}
  for count in range(min(p['max_parents'],len(parents))+1):
   for par in itertools.combinations(parents,count):
    rows[','.join(map(str,par))]=solve([[cov[i][j] for j in par] for i in par],[cov[i][b] for i in par]) if par else []
  out.append(rows)
 return out
