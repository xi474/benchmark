def compute(p):
 leaves={tuple(r['signals']):r['weight'] for r in p['scenarios']}
 return [[list(h),leaves.get(h)] for h in sorted({k[:i] for k in leaves for i in range(1,len(k)+1)})]
