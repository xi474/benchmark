from itertools import product
def compute(p):
 offers=sorted(p['offers']);return sorted((sum(n*r[2] for n,r in zip(q,offers)),sum(q),q) for q in product(*(range(o[3]+1) for o in offers)))
