def compute(p):
 return [[sorted({m['old'] for m in stmt if m['op']!='I'}) for stmt in tx['statements']] for tx in p['txs']]
