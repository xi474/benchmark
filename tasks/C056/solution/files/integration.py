from collections import Counter


def combine(p, left, right):
    facts=dict(p['initial']);result={}
    pools={k:0 for k in p['pools']}
    feeds={host:{stream:0 for stream in group} for host,group in p['feeds'].items()}
    todo={t['id']:t for t in p['tasks']}
    for ready in left:
        increments=Counter()
        for k in ready:
            t=todo.pop(k);pool=t['pool'];stream=t['stream']
            hosts=p['pools'][pool];host=hosts[pools[pool]%len(hosts)];pools[pool]+=1
            options=right[host][stream]
            items,n,total=options[feeds[host][stream]%len(options)];feeds[host][stream]+=1
            parent=sum(result[n]['delta'] for n in t['needs'])
            base=facts[host]
            delta=(base*n+total)*(1+parent)
            increments[host]+=delta
            result[k]=dict(host=host,items=items,base=base,parent=parent,delta=delta,attempts=t['attempts'])
        for host,v in increments.items():facts[host]+=v
    return dict(tasks=result,facts=facts,pool_reads=pools,feed_reads=feeds)

from pathlib import Path
import json

