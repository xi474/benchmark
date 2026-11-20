from collections import Counter
def accepted(value,expected):
 try:
  clusters=value['clusters'];ids=expected['ids'];seen=[];pred={}
  for index,group in enumerate(clusters):
   for ident in group:seen.append(ident);pred[ident]=index
  if len(seen)!=len(set(seen)) or set(seen)!=set(ids):return False
  true=expected['truth']
  def metrics(subset):
   a=Counter(pred[i] for i in subset);b=Counter(true[i] for i in subset);cross=Counter((pred[i],true[i]) for i in subset)
   choose=lambda n:n*(n-1)//2
   tp=sum(choose(n) for n in cross.values());pp=sum(choose(n) for n in a.values());tt=sum(choose(n) for n in b.values())
   precision=tp/pp if pp else 1.;recall=tp/tt if tt else 1.;f1=2*precision*recall/(precision+recall) if precision+recall else 0.
   return precision,recall,f1
  return all(x+1e-12>=y for x,y in zip(metrics(ids),expected['global_threshold'])) and all(x+1e-12>=y for x,y in zip(metrics(expected['stress_ids']),expected['stress_threshold']))
 except (KeyError,TypeError,ValueError):return False
