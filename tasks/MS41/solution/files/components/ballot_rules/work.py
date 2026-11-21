from fractions import Fraction
def compute(p):
 total=sum(p['profiles'].values());priors={k:[q.numerator,q.denominator] for k,v in p['profiles'].items() for q in [Fraction(v,total)]}
 n=len(p['answers']);tables={}
 for m in p['methods']:
  rows={};pending=[(0,)*n]
  while pending:
   counts=pending.pop();key=','.join(map(str,counts))
   if key in rows:continue
   left=m['votes']-sum(counts);leader=max(range(n),key=lambda i:(counts[i],-i))
   decided=sum(counts)>0 and all((counts[leader],-leader)>(counts[j]+left,-j) for j in range(n) if j!=leader)
   rows[key]=leader if decided else None
   if not decided:
    for i in range(n):pending.append(counts[:i]+(counts[i]+1,)+counts[i+1:])
  tables[m['id']]=rows
 return [priors,tables]
