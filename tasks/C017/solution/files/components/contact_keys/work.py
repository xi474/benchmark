def compute(p):
 return [[r.get('email','').strip().lower() for r in batch] for batch in p['batches']]
