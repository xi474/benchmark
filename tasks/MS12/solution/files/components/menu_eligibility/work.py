def compute(p):
 return {k:[r['id'] for r in p['recipes'] if r['difficulty']<=4 and set(r['ingredients'])<=set(items) and all(not set(r['ingredients']).intersection(g[2]) for g in p['groups'])] for k,items in p['delivery'].items()}
