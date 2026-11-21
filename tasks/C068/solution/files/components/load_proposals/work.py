def compute(p):
 return {str(i):[e['time']+e.get('delay',0),e.get('value'),e.get('error')] for i,e in enumerate(p['events']) if e['op']=='get'}
