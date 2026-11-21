def compute(p):
 return sorted(p['events'],key=lambda e:(e['visible'],e['id']))
