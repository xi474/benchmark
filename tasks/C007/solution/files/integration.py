import re
from datetime import datetime
from collections import defaultdict
def canonical(record):
 source=record['source'];v=record['fields']
 if source=='mobile':first,last=v['first'],v['last'];dob=datetime.strptime(v['dob'],'%Y-%m-%d').date().isoformat();ssn=v['ssn'];mail=v['email'];phone=v['phone'];address=v['address']
 elif source=='internet':first,last=v['full_name'].split(' ',1);dob=datetime.strptime(v['birth_date'],'%m/%d/%Y').date().isoformat();ssn='';mail=v['mail'];phone=v['tel'];address=v['street']
 elif source=='cable':last,first=v['last_first'].split(',',1);dob=datetime.strptime(v['birth'],'%Y%m%d').date().isoformat();ssn=v['government_id'];mail=v['contact'];phone=v['phone'];address=v['location']
 else:first,last=v['customer'].split(' ',1);dob=datetime.strptime(v['date_of_birth'],'%d %b %Y').date().isoformat();ssn='';mail=v['email'];phone=v['telephone'];address=v['address']
 letters=lambda s:re.sub('[^a-z0-9]','',s.lower())
 return dict(id=record['id'],first=letters(first),last=letters(last),dob=dob,ssn=re.sub('[^0-9]','',ssn),mail=letters(mail),phone=re.sub('[^0-9]','',phone),address=letters(address))
def close(a,b):
 if a==b:return True
 if abs(len(a)-len(b))>1:return False
 if len(a)==len(b):return sum(x!=y for x,y in zip(a,b))<=1
 if len(a)>len(b):a,b=b,a
 return any(a==b[:i]+b[i+1:] for i in range(len(b)))
def combine(p, left, right):
 rows=[v for _,v in sorted(left+right)];n=len(rows);parent=list(range(n));names=[{r['first']} if r['first'] not in p['ambiguous_names'] else set() for r in rows];birth=[{r['dob']} for r in rows];strong=[{r['ssn']} if len(r['ssn'])==9 else set() for r in rows]
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 blocks=defaultdict(list)
 for i,r in enumerate(rows):
  for k in ['phone','address']:
   if r[k]:blocks[(k,r[k])].append(i)
 pairs=set()
 for group in blocks.values():
  for j,i in enumerate(group):
   for k in group[:j]:pairs.add((k,i))
 edges=[]
 for i,j in pairs:
  a,b=rows[i],rows[j]
  score=0
  if a['dob']!=b['dob']:continue
  if len(a['ssn'])==len(b['ssn'])==9:
   if a['ssn']!=b['ssn']:continue
   score=100
  if a['ssn'] and b['ssn'] and min(len(a['ssn']),len(b['ssn']))>=4 and (a['ssn'].endswith(b['ssn']) or b['ssn'].endswith(a['ssn'])):score=max(score,80)
  if a['mail'] and b['mail'] and close(a['mail'],b['mail']):score=max(score,50 if a['mail']==b['mail'] else 40)
  if a['first']==b['first'] and a['first'] not in p['ambiguous_names'] and a['last']==b['last']:score=max(score,20)
  if score:edges.append((-score,i,j))
 for _,i,j in sorted(edges):
  a,b=find(i),find(j)
  if a==b:continue
  if len(names[a]|names[b])>1 or len(birth[a]|birth[b])>1 or len(strong[a]|strong[b])>1:continue
  parent[b]=a;names[a]|=names[b];birth[a]|=birth[b];strong[a]|=strong[b]
 groups=defaultdict(list)
 for i,r in enumerate(rows):groups[find(i)].append(r['id'])
 return dict(clusters=sorted([sorted(g) for g in groups.values()]))
