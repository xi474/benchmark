def compute(p):
 slots={k:t for k,t,q in p['slots']}
 return {k:[n,sorted({s for s in names if s in slots and due-7<=slots[s]<due})] for k,due,n,names in p['assignments'] if due is not None}
