def compute(p):
 return [[dict(name=' '.join(r.get('name','').split()),city=' '.join(r.get('city','').split()),source=r['source'],time=r['time']) for r in batch] for batch in p['batches']]
