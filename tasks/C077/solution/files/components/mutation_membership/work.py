def compute(p):
 active=set();out={}
 for i,e in enumerate(p['events']):
  if e['op']=='start':active.add(e['id'])
  elif e['op']=='finish':active.remove(e['id'])
  else:continue
  out[str(i)]=sorted(active)
 return out
