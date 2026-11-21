def compute(p):
 return {str(i):['snapshot_updated',e['revision']] if e.get('changed') else ['poll_unchanged',None] for i,e in enumerate(p['events']) if e['op']=='complete'}
