def compute(p):
    return [[r['a'],r['b'],r.get('from',0),r.get('to',10**18)] for r in p['links']+p['merges']]
