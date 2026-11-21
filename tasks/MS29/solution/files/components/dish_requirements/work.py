from itertools import combinations
from collections import Counter
def compute(p):
 out=[]
 for ds in combinations(sorted(d for d in p['dishes'] if d[2]<=p['max_difficulty']),3):
  if len({d[1] for d in ds})==3:
   needs=Counter()
   for d in ds:needs.update(d[3])
   out.append([[d[0] for d in ds],dict(needs)])
 return out
