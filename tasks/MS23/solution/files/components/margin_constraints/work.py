def compute(p):
 return [[all(sum(a)==sum(c) for a,c in zip(q['ab'],q['ac'])),[v for row in q['ac'] for v in row]] for q in p['snapshots']]
