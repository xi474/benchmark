from fractions import Fraction as F
def compute(p):
    last=max(r[1] for r in p['market'])
    ranked=sorted([row for row in p['market'] if row[1]>=last-29],key=lambda r:(-F(abs(r[3]-r[2]),r[2]),r[0]))[:p['top']]
    return [r[0] for r in ranked]
