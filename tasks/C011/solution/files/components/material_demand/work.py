from collections import Counter
def requirements(sku,qty,p):
 if sku not in p['bom']:return Counter({sku:qty})
 out=Counter()
 for child,amount in p['bom'][sku].items():out.update(requirements(child,qty*amount,p))
 return out
def compute(p):
 return {o['id']:dict(requirements(o['sku'],o['qty'],p)) for o in p['orders']}
