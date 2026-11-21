def compute(p):
 return [sorted(s['finish'],key=lambda path:path.count('/')) for s in p['scans']]
