def compute(p):
 next_at=p['ttl']*16;out={}
 for i,e in enumerate(p['events']):
  if e['op']=='get' and e['time']>=next_at:
   next_at=e['time']+p['ttl']*16;out[str(i)]=next_at
 return out
