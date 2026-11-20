#!/bin/bash
set -eu
cd /app
cat > solution.py <<'MEDIUM69_REFERENCE'
from collections import Counter


def transform(p):
    facts=dict(p['initial']);result={}
    pools={k:0 for k in p['pools']}
    feeds={host:{stream:0 for stream in group} for host,group in p['feeds'].items()}
    todo={t['id']:t for t in p['tasks']}
    while todo:
        ready=sorted(k for k,t in todo.items() if all(n in result for n in t['needs']))
        increments=Counter()
        for k in ready:
            t=todo.pop(k);pool=t['pool'];stream=t['stream']
            hosts=p['pools'][pool];host=hosts[pools[pool]%len(hosts)];pools[pool]+=1
            options=p['feeds'][host][stream]
            items=options[feeds[host][stream]%len(options)];feeds[host][stream]+=1
            parent=sum(result[n]['delta'] for n in t['needs'])
            base=facts[host]
            delta=sum((base+x)*(1+parent) for x in items)
            increments[host]+=delta
            result[k]=dict(host=host,items=items,base=base,parent=parent,delta=delta,attempts=t['attempts'])
        for host,v in increments.items():facts[host]+=v
    return dict(tasks=result,facts=facts,pool_reads=pools,feed_reads=feeds)

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
