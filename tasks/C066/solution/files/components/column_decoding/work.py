def decode(m):
 result={}
 if m['op']=='D':return result
 for c in m['cols']:
  k,typ,v=c['name'],c['type'],c['value']
  if typ!=('int' if k=='rank' else 'text'):return None
  try:result[k]=int(v) if k=='rank' and v is not None else v
  except ValueError:return None
 return result
def compute(p):
 return [[[decode(m) for m in stmt] for stmt in tx['statements']] for tx in p['txs']]
