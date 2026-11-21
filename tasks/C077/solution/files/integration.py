"""Author-only mailbox list reducer with a virtual clock."""


def combine(payload, left, right):
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
    for i,e in enumerate(payload['events']):
        now=e['time'];due(now);op=e['op']
        if op=='start':
            active=set(left[str(i)])
            log.append(dict(time=now,event='modification_started',id=e['id']))
        elif op=='finish':
            active=set(left[str(i)]);owed=True;loading=True
            log.append(dict(time=now,event='modification_finished',id=e['id']))
            issue(now)
        elif op=='refresh':
            owed=True;loading=True;issue(now)
        elif op=='response':
            assert flight==e['id'] and timer is None
            if right[str(i)] and right[str(i)][0]=='failure':
                flight=None;timer=right[str(i)][1];owed=True;loading=True
                log.append(dict(time=now,event='retry_scheduled',due=timer,reason='failure'))
            elif right[str(i)]:
                # The stale request remains in-flight until its fixed-delay timer fires.
                timer=right[str(i)][1];owed=True;loading=True
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
