def compute(p):
 out=dict.fromkeys(p['buyers'],0)
 for order in p['orders']:
  for cats,n,price in order['lines']:
   if set(cats)&{'Cameras','Electronics'}:out[order['buyer']]+=n*price
 return out
