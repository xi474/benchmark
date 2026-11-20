import itertools
from collections import Counter
def requirements(sku,qty,p):
 if sku not in p['bom']:return Counter({sku:qty})
 out=Counter()
 for child,amount in p['bom'][sku].items():out.update(requirements(child,qty*amount,p))
 return out
def time_options(order,p):
 if order['sku'] not in p['released']:return
 routing=p['routing'][order['sku']];duration=routing['setup']+routing['per_unit']*order['qty']
 for line in p['lines']:
  if order['sku'] not in line['qualified']:continue
  wip=[w for w in p['wip'] if w['line']==line['id']];earliest=max([p['freeze']]+[w['end']+p['changeover'] for w in wip])
  for start in range(earliest,order['due']-duration+1):
   end=start+duration
   if any(a<=start and end<=b for a,b in line['windows']):yield line['id'],start,end
def allocations(need,end,p):
 lots=sorted(p['lots'],key=lambda l:l['id']);components=sorted(need);answers=[]
 def component(i,used,rows):
  if i==len(components):answers.append(rows);return
  comp=components[i];compatible=[l for l in lots if l['material'] in p['substitutes'].get(comp,[comp]) and l['status']=='PASS' and l['expiry']>=end]
  def distribute(j,left,local,usednow):
   if j==len(compatible):
    if left==0:component(i+1,usednow,rows+local)
    return
   lot=compatible[j]
   for amount in range(min(left,lot['qty']-usednow.get(lot['id'],0))+1):
    copied=usednow.copy();copied[lot['id']]=copied.get(lot['id'],0)+amount
    distribute(j+1,left-amount,local+([(comp,lot['id'],amount)] if amount else []),copied)
  distribute(0,need[comp],[],used.copy())
 component(0,{},[])
 return answers
def schedule_ok(rows,p):
 allrows=rows+p['wip']
 for a,b in itertools.combinations(allrows,2):
  if a['line']==b['line'] and not (a['end']+p['changeover']<=b['start'] or b['end']+p['changeover']<=a['start']):return False
 consumed=Counter(lot for a in rows for comp,lot,qty in a['alloc'] for _ in range(qty))
 return all(consumed[l['id']]<=l['qty'] for l in p['lots'])
def plan_key(rows,p):
 chosen={a['id'] for a in rows};orders=sorted(p['orders'],key=lambda o:(o['priority'],o['due'],o['id']));totals=tuple(-sum(o['qty'] for o in orders if o['id'] in chosen and o['priority']==pr) for pr in [1,2,3]);bits=tuple(-int(o['id'] in chosen) for o in orders)
 desc=tuple((a['id'],a['line'],a['start'],a['end'],tuple(a['alloc'])) for a in sorted(rows,key=lambda a:a['id']))
 return totals,bits,desc
def assemble(rows,p):
 ordermap={o['id']:o for o in p['orders']};erp=[];mes=[];wms=[]
 for a in sorted(rows+p['wip'],key=lambda a:a['id']):
  wip=a in p['wip'];o=a if wip else ordermap[a['id']]
  erp.append(dict(wo=a['id'],run=p['run_id'],sku=o['sku'],qty=o['qty'],due=o['due'],start=a['start'],end=a['end'],line=a['line'],status='WIP_CONT' if wip else 'PLANNED',parent=None if wip else o['id']))
 for line in sorted(p['lines'],key=lambda x:x['id']):
  entries=sorted([a for a in erp if a['line']==line['id']],key=lambda a:(a['start'],a['wo']))
  for seq,a in enumerate(entries,1):mes.append(dict(run=p['run_id'],line=line['id'],seq=seq,wo=a['wo'],qty=a['qty'],start=a['start'],end=a['end'],status=a['status']))
 allocations_rows=sorted((a['id'],comp,lot,qty) for a in rows for comp,lot,qty in a['alloc'])
 for n,(wo,comp,lot,qty) in enumerate(allocations_rows,1):wms.append(dict(reservation=f'r{n:04d}',run=p['run_id'],wo=wo,component=comp,lot=lot,qty=qty,status='RESERVED'))
 return {'selected':sorted(a['id'] for a in rows),'erp':{'run':{'id':p['run_id'],'freeze':p['freeze']},'orders':erp},'mes':mes,'wms':wms}

def transform(p):
 orders=sorted(p['orders'],key=lambda o:o['id']);options={}
 for o in orders:
  options[o['id']]=[dict(id=o['id'],line=line,start=start,end=end,alloc=alloc) for line,start,end in time_options(o,p) for alloc in allocations(requirements(o['sku'],o['qty'],p),end,p)]
 best=None;answer=[]
 def visit(i,rows):
  nonlocal best,answer
  if i==len(orders):
   key=plan_key(rows,p)
   if best is None or key<best:best=key;answer=rows[:]
   return
  visit(i+1,rows)
  for a in options[orders[i]['id']]:
   if schedule_ok(rows+[a],p):visit(i+1,rows+[a])
 visit(0,[])
 return assemble(answer,p)

from pathlib import Path
import json
def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def build_component(input_path,output_path):
    value=transform(load_payload(input_path))
    p=Path(output_path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return value
