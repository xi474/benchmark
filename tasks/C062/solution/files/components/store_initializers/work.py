def compute(p):
 return {str(i):dict(backend=e['backend'],state='open',job=None,revision=e.get('revision',0),closed_at=None,updates=0) for i,e in enumerate(p['events']) if e['op']=='open'}
