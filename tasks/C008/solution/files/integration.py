def combine(p, left, right):
    import hashlib
    def canonical(node,time):
        from collections import defaultdict
        adj=defaultdict(set)
        for a,b,start,stop in left:
            if start<=time<stop:
                a,b=tuple(a),tuple(b);adj[a].add(b);adj[b].add(a)
        reached={node};queue=[node]
        while queue:
            for n in adj[queue.pop()]:
                if n not in reached:reached.add(n);queue.append(n)
        return min(reached)
    result=[]
    for table,ident,time,node in right:
        root=canonical(tuple(node),time)
        raw=json_compact([str(p['seed']),*root])
        token='ref_'+hashlib.sha256(raw.encode()).hexdigest()[:12]
        result.append(dict(table=table,id=ident,time=time,token=token))
    return dict(records=result)

def json_compact(value):
    import json
    return json.dumps(value,ensure_ascii=True,separators=(',',':'))

from pathlib import Path
import json
