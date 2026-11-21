def combine(p, left, right):
    nodes=p["nodes"].copy()
    idx=p["initial"].copy()
    report=[]
    for views,paths in zip(left,right):
        previous=idx.copy()
        for path in paths:
            files,dirs=views[path]
            prefix=path+"/"
            for key in list(idx):
                if not key.startswith(prefix):continue
                relative=key[len(prefix):]
                first,slash,_=relative.partition("/")
                if (slash and first not in dirs) or (not slash and first not in files):
                    del idx[key]
            idx.update({prefix+name:ident for name,ident in files.items()})
        def reverse(mapping):
            result={}
            for name,ident in sorted(mapping.items()):
                result.setdefault(ident,[]).append(name)
            return result
        left,right=reverse(previous),reverse(idx)
        changes={k:[left.get(k,[]),right.get(k,[])] for k in left.keys()|right.keys() if left.get(k)!=right.get(k)}
        report.append(dict(index=idx.copy(),changed=changes))
    return report

from pathlib import Path
import json

