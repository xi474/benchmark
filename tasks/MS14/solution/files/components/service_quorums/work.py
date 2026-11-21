def compute(p):
 return {s['id']:[s['need'],s['inputs']] for s in p['services']}
