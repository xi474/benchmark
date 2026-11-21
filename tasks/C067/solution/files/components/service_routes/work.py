from copy import deepcopy
def compute(p):
 cfg=deepcopy(p['clusters']);out={}
 for i,e in enumerate(p['events']):
  if e['op']=='service':cfg[e['cluster']]['services'][e['service']]=e['available']
  if e['op']=='request':
   c=cfg.get(e['cluster'],{});out[str(i)]=[c.get('mode'),c.get('services',{}).get(e['service'],False)]
 return out
