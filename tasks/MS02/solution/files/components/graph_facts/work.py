def compute(p):
 return [list(e) for e in sorted(set(map(tuple,p['graph'])))]
