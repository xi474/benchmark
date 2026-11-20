def transform(p):
    from copy import deepcopy
    accepted={};pending={};results=[]
    def norm(r):
        q=dict(email=r.get('email','').strip().lower(),name=' '.join(r.get('name','').split()),city=' '.join(r.get('city','').split()),source=r['source'],time=r['time'])
        return q
    for batch in p['batches']:
        a,b=deepcopy(accepted),deepcopy(pending);messages=[];failed=False
        for raw in batch:
            r=norm(raw);key=r['email'];old=a.get(key) or b.get(key)
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
def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def build_component(input_path,output_path):
    value=transform(load_payload(input_path))
    p=Path(output_path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return value
