from copy import deepcopy
def compute(p):
 user=deepcopy(p['user']);out={}
 for i,e in enumerate(p['events']):
  if e['op']=='update_user':user.update({k:deepcopy(e[k]) for k in ('roles','traits') if k in e})
  else:out[str(i)]=deepcopy(user)
 return out
