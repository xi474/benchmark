def compute(p):
 return [{k:list(bytes.fromhex(v)) for k,v in p.get('files',{}).items()},list(bytes.fromhex(p.get('stdin_hex','')))]
