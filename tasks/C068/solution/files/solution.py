"""Author-only event heap implementation of a single-flight TTL cache."""
import heapq


def transform(payload):
    ttl=payload['ttl'];cache={};flights={};results={};loads=[];heap=[];seq=0
    order=[];next_cleanup=ttl*16
    def settle(until):
        nonlocal next_cleanup
        while heap and heap[0][0]<=until:
            at,serial,key=heapq.heappop(heap)
            f=flights.pop(key)
            value=f['value'];error=f['error']
            cache[key]=dict(value=value,error=error,expires=at+ttl)
            for waiter in f['waiters']:
                if results[waiter] is None:
                    results[waiter]=dict(id=waiter,status='error' if error is not None else 'ok',
                                         value=None if error is not None else value,error=error,finished_at=at)
    for e in payload['events']:
        now=e['time'];settle(now)
        if e['op']=='get':
            ident,key=e['id'],e['key'];order.append(ident);results[ident]=None
            if now>=next_cleanup:
                cache={k:v for k,v in cache.items() if v['expires']>now}
                next_cleanup=now+ttl*16
            if key in cache and cache[key]['expires']<=now:
                del cache[key]
            if key in cache:
                v=cache[key]
                results[ident]=dict(id=ident,status='error' if v['error'] is not None else 'ok',
                    value=None if v['error'] is not None else v['value'],error=v['error'],finished_at=now)
            elif key in flights:
                flights[key]['waiters'].append(ident)
            else:
                seq+=1
                f=dict(value=e.get('value'),error=e.get('error'),waiters=[ident])
                flights[key]=f
                done=now+e['delay']
                loads.append(dict(key=key,started_at=now,finished_at=done))
                heapq.heappush(heap,(done,seq,key))
                settle(now)
        elif e['op']=='cancel':
            ident=e['id']
            if results[ident] is None:
                results[ident]=dict(id=ident,status='cancelled',value=None,error='cancelled',finished_at=now)
    assert all(v is not None for v in results.values())
    return dict(results=[results[i] for i in order],loads=loads,
                cache=[dict(key=k,**v) for k,v in sorted(cache.items())],next_cleanup=next_cleanup)

from pathlib import Path
import json
def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def build_component(input_path,output_path):
    value=transform(load_payload(input_path))
    p=Path(output_path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return value
