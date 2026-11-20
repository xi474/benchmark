"""Author-only request authorization and expiring credential reference."""
from copy import deepcopy


def transform(payload):
    clusters=deepcopy(payload['clusters'])
    policies=deepcopy(payload['policies'])
    cache={};issued=0;auth_calls=0;service_calls=0;remote_routes=0
    replies=[]
    for e in payload['events']:
        now=e['time'];op=e['op']
        if op=='policy':
            policies[e['user']]=deepcopy(e['allow']);continue
        if op=='service':
            clusters[e['cluster']]['services'][e['service']]=e['available'];continue
        if op=='request':
            auth_calls+=1
            user,cluster,service=e['user'],e['cluster'],e['service']
            allowed=any(x['cluster']==cluster and x['verb']==e['verb'] and
                        (x.get('service','*') in ['*',service]) for x in policies.get(user,[]))
            if not allowed:
                replies.append(dict(id=e['id'],status='denied'));continue
            service_calls+=1
            config=clusters[cluster]
            if not config['services'].get(service,False):
                replies.append(dict(id=e['id'],status='not_found'));continue
            if config['mode']=='local':
                replies.append(dict(id=e['id'],status='ok',credential='local',route='local'));continue
            remote_routes+=1
            cache={k:v for k,v in cache.items() if v['expires']>now}
            key=(user,cluster,service)
            if key not in cache:
                issued+=1
                cache[key]=dict(credential='cert-'+str(issued),expires=now+payload['ttl'])
            replies.append(dict(id=e['id'],status='ok',credential=cache[key]['credential'],route='reverse_tunnel'))
    return dict(replies=replies,authorizer_calls=auth_calls,service_lookups=service_calls,
                remote_routes=remote_routes,certificates_issued=issued,
                cache=[dict(user=k[0],cluster=k[1],service=k[2],**v) for k,v in sorted(cache.items())])

from pathlib import Path
import json
def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def build_component(input_path,output_path):
    value=transform(load_payload(input_path))
    p=Path(output_path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return value
