"""Author-only mailbox list reducer with a virtual clock."""


def transform(payload):
    active=set();owed=False;loading=False;flight=None;timer=None;fetches=[];commits=[];log=[];items=[];now=0;counter=0
    def issue(t):
        nonlocal owed,flight,loading,counter
        if active or flight is not None or timer is not None or not owed:return
        counter+=1;flight='fetch-'+str(counter);owed=False;loading=True
        fetches.append(dict(id=flight,time=t));log.append(dict(time=t,event='fetch',id=flight))
    def due(t):
        nonlocal timer,flight,owed,loading
        if timer is not None and timer<=t:
            at=timer;timer=None;flight=None;owed=True;loading=True
            issue(at)
    for e in payload['events']:
        now=e['time'];due(now);op=e['op']
        if op=='start':
            active.add(e['id'])
            log.append(dict(time=now,event='modification_started',id=e['id']))
        elif op=='finish':
            active.remove(e['id']);owed=True;loading=True
            log.append(dict(time=now,event='modification_finished',id=e['id']))
            issue(now)
        elif op=='refresh':
            owed=True;loading=True;issue(now)
        elif op=='response':
            assert flight==e['id'] and timer is None
            if e.get('failed'):
                flight=None;timer=now+2000;owed=True;loading=True
                log.append(dict(time=now,event='retry_scheduled',due=timer,reason='failure'))
            elif e.get('stale')==1:
                # The stale request remains in-flight until its fixed-delay timer fires.
                timer=now+1000;owed=True;loading=True
                log.append(dict(time=now,event='retry_scheduled',due=timer,reason='stale'))
            else:
                flight=None;items=e['items'];commits.append(dict(time=now,items=items))
                log.append(dict(time=now,event='committed',id=e['id']))
                loading=bool(owed)
                issue(now)
        elif op=='advance':
            pass
    return dict(fetches=fetches,commits=commits,events=log,state=dict(active=sorted(active),
                owed=owed,loading=loading,placeholders=loading,in_flight=flight,retry_at=timer,items=items))

from pathlib import Path
import json
def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def build_component(input_path,output_path):
    value=transform(load_payload(input_path))
    p=Path(output_path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return value
