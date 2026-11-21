def compute(p):
 rules=dict(p['policies']);out={}
 for i,e in enumerate(p['events']):
  if e['op']=='policy':rules[e['user']]=e['allow']
  if e['op']=='request':out[str(i)]=any(x['cluster']==e['cluster'] and x['verb']==e['verb'] and x.get('service','*') in ('*',e['service']) for x in rules.get(e['user'],[]))
 return out
