from collections import defaultdict
from fractions import Fraction as F
def compute(p):
    g=defaultdict(list)
    for s,c,v,full in p['grades']:
        if c in (16,17) and v is not None:g[s].append(F(v,full))
    tier={s:('P' if sum(y)*4>=3*len(y) else 'D' if sum(y)*5>=3*len(y) else 'N') for s,y in g.items()}
    return tier
