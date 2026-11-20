"""Author-only deterministic poller lifecycle reference."""


def transform(payload):
    stores, log = {}, []
    for e in payload['events']:
        t, key, op = e['time'], e['store'], e['op']
        if op == 'open':
            stores[key] = dict(backend=e['backend'], state='open', job=None,
                               revision=e.get('revision',0), closed_at=None, updates=0)
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
                if e.get('changed',False):
                    s['revision']=e['revision'];s['updates']+=1
                    event='snapshot_updated'
                else:
                    event='poll_unchanged'
                log.append(dict(time=t,store=key,event=event,job=s['job']))
                s['job']=None
    return {'events':log,'stores':stores}

from pathlib import Path
import json
def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def build_component(input_path,output_path):
    value=transform(load_payload(input_path))
    p=Path(output_path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return value
