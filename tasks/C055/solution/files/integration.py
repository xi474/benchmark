import json
import re
from functools import lru_cache


def combine(p, left, right):
    keys=left.keys()|right.keys()
    values={k:max((g[k] for g in (left,right) if k in g),key=lambda row:row[0])[1:] for k in keys}
    final={}
    for k,(loc,(pos,data,vault,trust)) in values.items():
        if vault and not p['tags']:
            if data not in p['keys']:return {'status':'sealed'}
            data=p['keys'][data];vault=False;trust=True
        final[k]=(loc,pos,data,vault,trust and not vault)
    @lru_cache(None)
    def render(k):
        _,_,data,vault,trust=final[k]
        if vault:return '[sealed]'
        if not trust:return data
        return re.sub(r'\$\{([a-z]+)\}',lambda m:render(m.group(1)),data)
    entries=[];lines=[]
    for k,(loc,pos,data,vault,trust) in sorted(final.items()):
        entries.append([k,loc,pos,trust,render(k)])
        lines.append(k+': '+('!vault ' if vault else '')+json.dumps(data,ensure_ascii=False)+'\n')
    return dict(status='ok',entries=entries,dump=''.join(lines))

from pathlib import Path
import json

