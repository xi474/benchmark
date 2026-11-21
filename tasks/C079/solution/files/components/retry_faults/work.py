def compute(p):
 return {k:sorted({i for i in v if 0<=i<=p['max_retries']}) for k,v in p.get('corrupt_attempts',{}).items()}
