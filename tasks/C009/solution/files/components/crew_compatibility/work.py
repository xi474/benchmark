def compute(p):
 return {v['id']:[d['id'] for d in p['drivers'] if v['type'] in d['types']] for v in p['vehicles']}
