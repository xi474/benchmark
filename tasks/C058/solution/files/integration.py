"""Reference tree interpreter. Author-only; never copy into the actor package."""
from copy import deepcopy


def combine(payload, left, right):
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
                if not left[host]['/'.join(map(str,path))][0]:
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
                    fail = left[host]['/'.join(map(str,path))][1]
                    steps.append((path, {'task':node['id'], 'kind':'task',
                                         'status':'failed' if fail else 'ok'}))
                    if not fail:
                        pending.update(right[1]['/'.join(map(str,path))])
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
                chosen = sorted(pending,key=right[0].__getitem__)
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
