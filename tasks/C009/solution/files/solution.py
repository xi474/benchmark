import itertools
def key(a):return (a['job'],a['start'],a['vehicle'],a['driver'],a['supplier'])
def candidates(job,p,cutoff):
 for v in p['vehicles']:
  if v['type']!=job['type'] or v['capacity']<job['quantity']:continue
  for d in p['drivers']:
   if v['type'] not in d['types']:continue
   for s in p['suppliers']:
    if s['id'] not in job['suppliers']:continue
    profit=job['revenue']-job['quantity']*s['unit_cost']-v['cost']*job['duration']
    for t in range(max(cutoff,job['release']),job['deadline']-job['duration']+1):
     if t>s['close']:continue
     yield dict(job=job['id'],vehicle=v['id'],driver=d['id'],supplier=s['id'],start=t,end=t+job['duration'],quantity=job['quantity'],profit=profit)
def legal(rows,p):
 for a,b in itertools.combinations(rows,2):
  if a['vehicle']==b['vehicle'] or a['driver']==b['driver']:
   if max(a['start'],b['start'])<min(a['end'],b['end']):return False
 for s in p['suppliers']:
  if sum(a['quantity'] for a in rows if a['supplier']==s['id'])>s['stock']:return False
 for d in p['drivers']:
  work=sorted([a for a in rows if a['driver']==d['id']],key=lambda a:a['start'])
  if sum(a['end']-a['start'] for a in work)>d['max_work']:return False
  continuous=0;last=None
  for a in work:
   if last is None or a['start']-last>=d['break']:continuous=0
   continuous+=a['end']-a['start']
   if continuous>d['max_continuous']:return False
   last=a['end']
 return True
def replay(p,optimizer):
 jobs={};cancelled=set();ignored=[];committed=[];snapshots=[];events=sorted(p['events'],key=lambda e:(e['visible'],e['id']));processed=set()
 for round in p['rounds']:
  cutoff=round['cutoff']
  for event in events:
   if event['visible']>cutoff or event['id'] in processed:continue
   processed.add(event['id'])
   if event['kind']=='request':jobs[event['job']['id']]=event['job']
   else:
    ident=event['job'];old=next((a for a in committed if a['job']==ident),None)
    if old and old['start']<cutoff:ignored.append(ident)
    else:
     cancelled.add(ident);committed=[a for a in committed if a['job']!=ident]
  todo=[j for j in jobs.values() if j['id'] not in cancelled and not any(a['job']==j['id'] for a in committed)]
  selected=optimizer(todo,committed,p,cutoff);combined=sorted(committed+selected,key=key)
  snapshots.append({'cutoff':cutoff,'assignments':combined,'profit':sum(a['profit'] for a in combined),'cancelled':sorted(cancelled),'ignored_cancellations':sorted(set(ignored))})
  if round['commit']:committed=combined
 return {'rounds':snapshots}

def optimize(jobs,fixed,p,cutoff):
 jobs=sorted(jobs,key=lambda j:j['id']);best=(0,0,());answer=[]
 def visit(i,rows,profit):
  nonlocal best,answer
  if i==len(jobs):
   desc=tuple(key(a) for a in sorted(rows,key=key));value=(-profit,-len(rows),desc)
   if value<best:best=value;answer=[a.copy() for a in rows]
   return
  visit(i+1,rows,profit)
  for a in candidates(jobs[i],p,cutoff):
   if legal(fixed+rows+[a],p):visit(i+1,rows+[a],profit+a['profit'])
 visit(0,[],0)
 return answer
def transform(p):return replay(p,optimize)

from pathlib import Path
import json
def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def build_component(input_path,output_path):
    value=transform(load_payload(input_path))
    p=Path(output_path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return value
