"""Reference tree interpreter. Author-only; never copy into the actor package."""
from copy import deepcopy


def transform(payload):
    hosts = payload['hosts']
    handlers = payload.get('handlers', [])
    phase_names = ['pre', 'roles', 'includes', 'tasks', 'post']
    streams = {}
    final = {}
    for host in hosts:
        steps, pending = [], set()

        def walk(nodes, prefix):
            ok = True
            for i, node in enumerate(nodes):
                path = prefix + (i,)
                if node.get('only') is not None and host not in node['only']:
                    continue
                if 'block' in node:
                    b = node['block']
                    success = walk(b.get('tasks', []), path+(0,))
                    if not success and b.get('rescue'):
                        success = walk(b['rescue'], path+(1,))
                    always_ok = walk(b.get('always', []), path+(2,))
                    if not success or not always_ok:
                        return False
                else:
                    fail = host in node.get('fail_hosts', [])
                    steps.append((path, {'task':node['id'], 'kind':'task',
                                         'status':'failed' if fail else 'ok'}))
                    if not fail:
                        pending.update(node.get('notify', []))
                    if fail:
                        return False
            return ok

        failed = False
        for phase_no, phase in enumerate(phase_names):
            if failed:
                break
            nodes = payload.get('program', {}).get(phase, [])
            failed = not walk(nodes, (phase_no,0))
            if pending:
                # A concrete flush exists only when this host has work to flush.
                chosen = [h for h in handlers if h in pending]
                steps.append(((phase_no,1), {'task':'flush_handlers', 'kind':'flush',
                                            'handlers':chosen, 'status':'ok'}))
                for j, name in enumerate(chosen):
                    steps.append(((phase_no,1,j), {'task':name,'kind':'handler','status':'ok'}))
                pending.clear()
        streams[host] = steps
        final[host] = 'failed' if failed else 'ok'
    cursors = {h:0 for h in hosts}
    batches = []
    while True:
        ready = [(streams[h][cursors[h]][0], h) for h in hosts
                 if cursors[h] < len(streams[h])]
        if not ready:
            break
        earliest = min(p for p,h in ready)
        pairs = []
        for path, host in ready:
            if path == earliest:
                pairs.append(dict(host=host, **deepcopy(streams[host][cursors[host]][1])))
                cursors[host] += 1
        batches.append(pairs)
    return {'batches':batches,'final':final}

from pathlib import Path
import json
def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def build_component(input_path,output_path):
    value=transform(load_payload(input_path))
    p=Path(output_path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return value
