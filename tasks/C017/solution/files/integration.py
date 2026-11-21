def combine(p, left, right):
    from copy import deepcopy
    accepted={};pending={};results=[]
    def norm(r):
        q=dict(email=r.get('email','').strip().lower(),name=' '.join(r.get('name','').split()),city=' '.join(r.get('city','').split()),source=r['source'],time=r['time'])
        return q
    for keys, batch in zip(left,right):
        a,b=deepcopy(accepted),deepcopy(pending);messages=[];failed=False
        for email, raw in zip(keys,batch):
            r=dict(raw,email=email);key=r['email'];old=a.get(key) or b.get(key)
            if old and any(old[k] and r[k] and old[k]!=r[k] for k in ['name','city']):failed=True;break
            sources=sorted(set((old or {}).get('sources',[])+[r['source']]))
            if key in a:
                # Accepted canonical audit record remains immutable; only source view expands.
                a[key]['sources']=sources;messages.append('duplicate');continue
            value=dict(email=key,name=r['name'] or (old or {}).get('name',''),city=r['city'] or (old or {}).get('city',''),first_contact=min(r['time'],old['first_contact']) if old else r['time'],sources=sources)
            if value['name'] and value['city']:
                a[key]=value;b.pop(key,None);messages.append('promoted' if old else 'accepted')
            else:b[key]=value;messages.append('incomplete')
        if failed:results.append(dict(status='rejected',items=[]))
        else:accepted,pending=a,b;results.append(dict(status='committed',items=messages))
    def rows(table):return [table[k] for k in sorted(table)]
    sources={}
    for r in rows(accepted)+rows(pending):
        for s in r['sources']:sources.setdefault(s,[]).append(r['email'])
    return dict(batches=results,accepted=rows(accepted),incomplete=rows(pending),sources={s:sorted(set(v)) for s,v in sorted(sources.items())})

from pathlib import Path
import json
