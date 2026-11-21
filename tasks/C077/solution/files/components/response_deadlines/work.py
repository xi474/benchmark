def compute(p):
 return {str(i):(['failure',e['time']+2000] if e.get('failed') else ['stale',e['time']+1000] if e.get('stale')==1 else None) for i,e in enumerate(p['events']) if e['op']=='response'}
