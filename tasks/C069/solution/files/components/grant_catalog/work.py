def compute(p):
 return {k:dict(approved=r.get('approved') is True,expiry=r['expiry'],roles=sorted(set(r.get('roles',[]))),resources=sorted(set(r.get('resources',[])))) for k,r in p.get('access_requests',{}).items()}
