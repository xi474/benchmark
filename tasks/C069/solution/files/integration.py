"""Author-only renewal state and encoded identity reference."""
from copy import deepcopy
import base64,json


def encode(kind,value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    return kind+'.'+base64.urlsafe_b64encode(raw).decode().rstrip('=')


def combine(payload, left, right):
    user=deepcopy(payload['user']);requests=right
    initial=dict(id=payload.get('initial_id','s0'),user=deepcopy(user),active=[],resources=[],
                 login_time=payload['start_time'],expiry=payload['start_time']+payload['session_ttl'])
    sessions={initial['id']:initial};replies=[]
    for i,e in enumerate(payload['events']):
        if e['op']=='update_user':continue
        old=sessions[e['prev']];now=e['time']
        if old['expiry']<=now:
            replies.append(dict(id=e['id'],status='expired'));continue
        current=deepcopy(old)
        current['id']=e['id']
        if e.get('reload_user'):current['user']=deepcopy(left[str(i)])
        if e.get('switchback'):
            current['active']=[];current['resources']=[]
        assumed=e.get('access_request')
        if assumed:
            req=requests[assumed]
            if req.get('approved') is not True or req['expiry']<=now:
                replies.append(dict(id=e['id'],status='request_unavailable'));continue
            resource_active=any(requests[r].get('resources') for r in current['active'])
            if req.get('resources') and resource_active:
                replies.append(dict(id=e['id'],status='resource_already_active'));continue
            if assumed not in current['active']:current['active'].append(assumed)
        # Expired grants cannot be silently carried forward through another renewal.
        if any(requests[r]['expiry']<=now for r in current['active']):
            replies.append(dict(id=e['id'],status='request_unavailable'));continue
        roles=set(current['user']['roles']);resources=set()
        for r in current['active']:
            roles.update(requests[r].get('roles',[]));resources.update(requests[r].get('resources',[]))
        current['resources']=sorted(resources)
        expiry=now+payload['session_ttl']
        if current['active']:expiry=min(expiry,*(requests[r]['expiry'] for r in current['active']))
        current['expiry']=expiry
        ssh=dict(roles=sorted(roles),allowed_resources=sorted(resources),extensions=deepcopy(current['user']['traits']),
                 login_time=current['login_time'],expires=expiry)
        tls=dict(user=current['user']['name'],active_requests=sorted(current['active']),
                 login_time=current['login_time'],expires=expiry)
        sessions[current['id']]=current
        replies.append(dict(id=current['id'],status='ok',ssh_certificate=encode('SSH-MODEL1',ssh),
                            tls_certificate=encode('TLS-MODEL1',tls)))
    return dict(replies=replies,session_ids=list(sessions))

from pathlib import Path
import json
