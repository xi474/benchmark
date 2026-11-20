#!/bin/bash
set -eu
cd /app
cat > solution.py <<'MEDIUM69_REFERENCE'
import json
import re
from functools import lru_cache


def transform(p):
    values={}
    for src in p['sources']:
        anchors={}
        for i,line in enumerate(src['yaml'].splitlines(),1):
            if line=='---':
                anchors={}
                continue
            if not line:continue
            key,body=line.split(': ',1)
            pos=[src['name'],i,len(key)+3]
            if body.startswith('*'):
                value=anchors[body[1:]]
            else:
                anchor=None
                if body.startswith('&'):
                    anchor,body=body[1:].split(' ',1)
                vault=body.startswith('!vault ')
                data=body[7:] if vault else body
                value=(pos,data,vault,src['trusted'])
                if anchor:anchors[anchor]=value
            values[key]=([src['name'],i,1],value)
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

def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value

MEDIUM69_REFERENCE
