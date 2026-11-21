def time_options(order,p):
 if order['sku'] not in p['released']:return
 routing=p['routing'][order['sku']];duration=routing['setup']+routing['per_unit']*order['qty']
 for line in p['lines']:
  if order['sku'] not in line['qualified']:continue
  wip=[w for w in p['wip'] if w['line']==line['id']];earliest=max([p['freeze']]+[w['end']+p['changeover'] for w in wip])
  for start in range(earliest,order['due']-duration+1):
   end=start+duration
   if any(a<=start and end<=b for a,b in line['windows']):yield line['id'],start,end
def compute(p):
 return {o['id']:list(time_options(o,p)) for o in p['orders']}
