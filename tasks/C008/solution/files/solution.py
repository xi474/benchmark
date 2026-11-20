def transform(p):
    import hashlib
    nodes=set()
    for r in p['records']:nodes.add((r['tenant'],r['subject']))
    for e in p['links']+p['merges']:nodes.update([tuple(e['a']),tuple(e['b'])])
    def canonical(node,time):
        adj={n:set() for n in nodes}
        for e in p['links']+p['merges']:
            if e.get('from',0)<=time<e.get('to',10**18):
                a,b=tuple(e['a']),tuple(e['b']);adj[a].add(b);adj[b].add(a)
        reached={node};queue=[node]
        while queue:
            for n in adj[queue.pop()]:
                if n not in reached:reached.add(n);queue.append(n)
        return min(reached)
    result=[]
    for r in p['records']:
        root=canonical((r['tenant'],r['subject']),r['time'])
        raw=json_compact([str(p['seed']),*root])
        token='ref_'+hashlib.sha256(raw.encode()).hexdigest()[:12]
        result.append(dict(table=r['table'],id=r['id'],time=r['time'],token=token))
    return dict(records=result)

def json_compact(value):
    import json
    return json.dumps(value,ensure_ascii=True,separators=(',',':'))

from pathlib import Path
import json
def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def build_component(input_path,output_path):
    value=transform(load_payload(input_path))
    p=Path(output_path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return value
