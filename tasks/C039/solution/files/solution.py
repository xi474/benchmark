import math,itertools
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
def topo(n,edges):
 done=[]
 while len(done)<n:
  avail=[i for i in range(n) if i not in done and all(a in done for a,b in edges if b==i)]
  if not avail:return None
  done.append(min(avail))
 return done

def transform(p):
 names=p['nodes'];n=len(names);cov=p['covariance'];allowed=[(names.index(a),names.index(b)) for a,b in p['allowed'] if b!=p['root']];best=None
 for edges in itertools.combinations(allowed,p['edge_count']):
  order=topo(n,edges)
  if order is None:continue
  score=0;coefs=[]
  for b in range(n):
   par=sorted(a for a,child in edges if child==b)
   if len(par)>p['max_parents']:break
   beta=solve([[cov[i][j] for j in par] for i in par],[cov[i][b] for i in par]) if par else []
   var=cov[b][b]-sum(v*cov[a][b] for a,v in zip(par,beta));score+=p['sample_size']*math.log(var)+len(par)*math.log(p['sample_size'])
   coefs.extend((names[a],names[b],round(v,6)) for a,v in zip(par,beta))
  else:
   desc=tuple(sorted((names[a],names[b]) for a,b in edges));key=(round(score,9),desc)
   if best is None or key<best[0]:best=(key,edges,order,coefs)
 if best is None:return {'feasible':False}
 key,edges,order,coefs=best;mean=p['mean'][:];do=p['intervention'];index=names.index(do['node']);mean[index]=do['value']
 # Recompute unrounded slopes for intervention propagation.
 for b in order:
  if b==index:continue
  par=sorted(a for a,child in edges if child==b)
  beta=solve([[cov[i][j] for j in par] for i in par],[cov[i][b] for i in par]) if par else []
  mean[b]=p['mean'][b]+sum(v*(mean[a]-p['mean'][a]) for a,v in zip(par,beta))
 return {'feasible':True,'edges':[list(x) for x in key[1]],'score':round(key[0],6),'coefficients':[list(x) for x in sorted(coefs)],'intervened_edges':[list(x) for x in key[1] if x[1]!=do['node']],'mean':[round(v,6) for v in mean]}

from pathlib import Path
import json
def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def build_component(input_path,output_path):
    value=transform(load_payload(input_path))
    p=Path(output_path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return value
