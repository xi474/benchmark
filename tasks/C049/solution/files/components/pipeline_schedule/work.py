def compute(p):
 w=p['world_size'];m=len(p['microbatches']);out=[]
 for bi in range(m):
  for s in range(w):
   out.append(dict(kind='forward',microbatch=bi,stage=s))
   if s<w-1:out.append(dict(kind='send_activation',microbatch=bi,source=s,target=s+1))
 for bi in reversed(range(m)):
  for s in reversed(range(w)):
   out.append(dict(kind='backward',microbatch=bi,stage=s))
   if s:out.append(dict(kind='send_gradient',microbatch=bi,source=s,target=s-1))
 n=len(p['layers'])
 return dict(events=out,partitions=[dict(stage=r,start=n*r//w,stop=n*(r+1)//w) for r in range(w)])
