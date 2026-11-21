def compute(p):
 out=[]
 for q in p['queries']:
  row=[]
  for t in range(q['start'],q['end']):
   events={}
   for d,at,seen,state in p['log']:
    if seen<=q['as_of'] and at<=t and (at,seen)>events.get(d,(-1,-1,''))[:2]:events[d]=(at,seen,state)
   row.append(sorted(d for d,v in events.items() if v[2]!='up'))
  out.append(row)
 return out
