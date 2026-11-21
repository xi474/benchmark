def compute(p):
 return {h:{k:[[v,len(v),sum(v)] for v in stream] for k,stream in group.items()} for h,group in p['feeds'].items()}
