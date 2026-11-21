def compute(p):
 return [{k:[t,q] for k,t,q in p['slots'] if k not in cancelled} for cancelled in p['withdrawals']]
