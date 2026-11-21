def compute(p):
 return dict(rc="PS1='PROMPT> '\nPS2='CONT> '\nHISTFILE=/dev/null\n"+p.get('startup','')+'\n',timeout=p.get('timeout_seconds',4),markers=[s['until'] for s in p['steps']])
