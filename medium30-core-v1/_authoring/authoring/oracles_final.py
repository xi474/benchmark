import calendar
import base64
import copy
from datetime import date,timedelta
import hashlib
import re

def final_expected(kind,p):
    if kind=='migration_policy':
        out={}
        for name,source in [('notes',p['notes']),('shelves',p['shelves'])]:
            rows=copy.deepcopy(source);changed=deleted=failed=0
            if p['old']!=p['new']:
                if p['new'] not in rows:rows={k:v for k,v in source.items() if k!=p['old']};rows[p['new']]=source[p['old']];changed=1
                elif name=='notes':failed=1
                else:rows={k:v for k,v in source.items() if k!=p['old']};deleted=1
            out[name]=dict(rows=rows,stats=dict(rows_changed=changed,rows_deleted=deleted,failed_deletes=failed))
        return out
    if kind=='template_ast_prefix':
        # Token scanner restricted to the same declared expression subset; no AST walker.
        dependencies={}
        for name,text in p['templates'].items():
            found=set()
            for expression in re.findall(r'\{\{(.*?)\}\}',text,re.S):
                for match in re.finditer(r'(?<![\w])conf((?:\.[A-Za-z_]\w*|\[\s*[\'\"][A-Za-z_]\w*[\'\"]\s*\])+)',expression):
                    chain=re.sub(r'\[\s*[\'\"](\w+)[\'\"]\s*\]',r'.\1',match.group(1)).lstrip('.')
                    eligible=[key for key in p['options'] if chain==key or chain.startswith(key+'.')]
                    if eligible:found.add(max(eligible,key=len))
            dependencies[name]=sorted(found)
        return dict(dependencies=dependencies,affected=sorted(name for name,deps in dependencies.items() if set(deps)&set(p['changed'])))
    if kind=='transaction_memory':
        state={k:{r['id']:r['name'] for r in rows} for k,rows in p['initial'].items()};pending=None;reads=[];routes=[]
        for e in p['events']:
            if e['kind']=='begin':pending=copy.deepcopy(state);continue
            if e['kind']=='commit':state=pending;pending=None;continue
            table=p['repositories'][e['repo']+'s']['table'];view=pending if pending is not None else state
            routes.append('transaction' if pending is not None else 'read' if e['kind']=='get' else 'write')
            if e['kind']=='get':reads.append(view[table].get(e['id']))
            else:view[table][e['id']]=e['name']
        return dict(reads=reads,routes=routes,final={table:[dict(id=i,name=rows[i]) for i in sorted(rows)] for table,rows in state.items()})
    if kind=='resource_manifest':
        selected=sorted({name for name in p['files'] for rule in p['patterns'] if name.rsplit('/',1)[0]==rule['directory'] and name.rsplit('/',1)[1].endswith(rule['extension'])})
        return dict(paths=selected,values=[p['files'][name] for name in p['requests']])
    if kind=='rental_sets':
        byid={x['id']:x for x in p['properties']};keep=[x for x in p['saved'] if byid[x]['city']!=p['city'] or p['low']<=byid[x]['price']<=p['high']];add=[x['id'] for x in p['properties'] if x['city']==p['city'] and p['low']<=x['price']<=p['high']]
        new=[e for e in p['events'] if 0<=e['at']<p['window'] and e['property']['city']==p['city'] and p['low']<=e['property']['price']<=p['high']]
        return dict(saved=sorted(set(keep+add)),notifications=[dict(to=p['friend'],property=e['property']['id'],at=e['at']) for e in sorted(new,key=lambda e:(e['at'],e['property']['id']))])
    if kind=='gift_recipient_set':
        emails=sorted([e for e in p['emails'] if e['at'] in range(p['window'])],key=lambda x:(x['at'],x['id']));senders=sorted(set(e['from'] for e in emails));variant=[v['id'] for v in p['variants'] if all(v.get(k)==x for k,x in p['selection'].items())][0];d=date.fromisoformat(p['date']);last=date(d.year+int(d.month==12),1 if d.month==12 else d.month+1,1)-timedelta(days=1)
        return dict(replies=[dict(email=e['id'],to=e['from'],at=p['window'],purpose='gift_reply') for e in emails],order=dict(at=p['window']+30,variant=variant,quantity=len(senders)),reminder=dict(date=last.isoformat(),all_day=True,title='Reminder: Hand Out Gifts'))
    if kind=='group_distinct_people':
        members=sorted(c['id'] for c in p['contacts'] if c['name'] in p['names']);first={}
        for e in p['messages']:
            if e['group']=='group:new' and e['sender'] in members and 0<=e['at']<p['window']:first[e['sender']]=min(first.get(e['sender'],p['window']),e['at'])
        values=sorted(first.values());t=values[p['threshold']-1] if len(values)>=p['threshold'] else None;group=dict(id='group:new',title='Happy Astrid Day!',members=members)
        return dict(group=group,trigger_at=t,ride=dict(at=t,pickup='21:30',vehicle='van',**{'from':'home'},to='Tegnergatan 8') if t is not None else None,notice=dict(at=t,meet='20:00') if t is not None else None,deleted=sorted(e['id'] for e in p['calendar'] if e['start_minute']>=1200) if t is not None else [])
    if kind=='document_partitions':
        data=p['files'][p['source']];checksum=hashlib.sha256(base64.b64decode(data)).hexdigest();files={k:v for k,v in p['files'].items() if k!=p['source']};files[p['destination']]=data;target=sorted(set([p['email_sender']]+[x['id'] for x in p['people'] if x['pilot'] and x['country']=='RU']));groups={True:[],False:[]}
        for x in p['people']:
            if x['id']!=p['self'] and x['teacher']:groups[x['messages']].append(x['id'])
        info=dict(path=p['destination'],sha256=checksum)
        return dict(files=files,target_email=dict(to=target,**info),messages=dict(members=sorted(groups[True]),**info) if groups[True] else None,fallback_email=dict(to=sorted(groups[False]),**info) if groups[False] else None,attachment_content=data)
    from oracles_storage import storage_expected
    return storage_expected(kind,p)
