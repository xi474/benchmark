"""Author-only deterministic poller lifecycle reference."""


def combine(payload, left, right):
    stores, log = {}, []
    for i,e in enumerate(payload['events']):
        t, key, op = e['time'], e['store'], e['op']
        if op == 'open':
            stores[key] = dict(left[str(i)])
            log.append(dict(time=t,store=key,event='opened'))
            continue
        s = stores[key]
        if op == 'poll':
            if s['state'] != 'open':
                log.append(dict(time=t,store=key,event='poll_rejected'))
            elif s['job'] is not None:
                log.append(dict(time=t,store=key,event='poll_coalesced'))
            else:
                s['job'] = e['job']
                log.append(dict(time=t,store=key,event='poll_started',job=e['job']))
        elif op == 'close':
            if s['state'] == 'closed':
                log.append(dict(time=t,store=key,event='close_returned'))
            elif s['job'] is None:
                s['state'],s['closed_at']='closed',t
                log.append(dict(time=t,store=key,event='close_returned'))
            elif s['state'] == 'open':
                s['state']='closing'
                log.append(dict(time=t,store=key,event='cancel_sent',job=s['job']))
            else:
                log.append(dict(time=t,store=key,event='close_waiting'))
        elif op == 'complete':
            assert s['job'] == e['job']
            if s['state'] == 'closing':
                log.append(dict(time=t,store=key,event='callback_cancelled',job=s['job']))
                s['job']=None
                s['state'],s['closed_at']='closed',t
                log.append(dict(time=t,store=key,event='close_returned'))
            else:
                event,revision=right[str(i)]
                if event=='snapshot_updated':s['revision']=revision;s['updates']+=1
                log.append(dict(time=t,store=key,event=event,job=s['job']))
                s['job']=None
    return {'events':log,'stores':stores}

from pathlib import Path
import json
