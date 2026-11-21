import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_contracts():
    contracts = {}
    for cp in sorted(ROOT.rglob('contract.json')):
        if 'outputs' in cp.relative_to(ROOT).parts:
            continue
        c = json.loads(cp.read_text(encoding='utf-8'))
        contracts[c['name']] = (cp, c)
    return contracts


def _topological_order(contracts):
    producer = {}
    for name, (cp, c) in contracts.items():
        out = c['output']
        if out in producer:
            raise ValueError('duplicate output: %s' % out)
        producer[out] = name

    deps = {}
    for name, (cp, c) in contracts.items():
        d = set()
        for inp in c['inputs']:
            if inp in producer:
                d.add(producer[inp])
        deps[name] = d

    order = []
    remaining = set(contracts)
    while remaining:
        ready = [n for n in remaining if deps[n] <= set(order)]
        if not ready:
            raise ValueError('dependency cycle detected')
        ready.sort()
        for n in ready:
            order.append(n)
            remaining.discard(n)
    return order


def main():
    contracts = _load_contracts()
    if not contracts:
        raise ValueError('no contracts')

    order = _topological_order(contracts)

    for name in order:
        cp, c = contracts[name]
        render = cp.with_name('render.py')
        subprocess.run(
            [sys.executable, str(render), str(ROOT), str(cp)],
            cwd=ROOT,
            check=True,
        )

    subprocess.run(
        [sys.executable, str(ROOT / 'integrate.py')],
        cwd=ROOT,
        check=True,
    )

    subprocess.run(
        [sys.executable, str(ROOT / 'final_report.py')],
        cwd=ROOT,
        check=True,
    )


if __name__ == '__main__':
    main()
