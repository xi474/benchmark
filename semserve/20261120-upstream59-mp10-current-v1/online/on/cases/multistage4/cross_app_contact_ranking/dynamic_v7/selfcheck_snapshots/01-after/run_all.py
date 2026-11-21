import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_contracts():
    contracts = []
    for cp in sorted(ROOT.rglob('contract.json')):
        if 'outputs' in cp.relative_to(ROOT).parts:
            continue
        contracts.append(cp)
    if not contracts:
        raise ValueError('no contracts')
    return contracts


def _topological_order(contracts):
    # Build dependency graph keyed by component name.
    by_name = {}
    for cp in contracts:
        c = json.loads(cp.read_text(encoding='utf-8'))
        by_name[c['name']] = (cp, c)

    # Map output path -> producing component name.
    producer = {}
    for name, (cp, c) in by_name.items():
        producer[c['output']] = name

    # Build edges: component depends on components that produce its inputs.
    deps = {}
    for name, (cp, c) in by_name.items():
        d = set()
        for inp in c['inputs']:
            if inp in producer:
                d.add(producer[inp])
        deps[name] = d

    # Kahn's algorithm.
    order = []
    remaining = set(by_name)
    while remaining:
        ready = [n for n in remaining if deps[n] <= set(order)]
        if not ready:
            raise ValueError('dependency cycle detected')
        ready.sort()
        for n in ready:
            order.append(n)
            remaining.discard(n)
    return [by_name[n][0] for n in order]


def main():
    contracts = _load_contracts()
    ordered = _topological_order(contracts)
    for cp in ordered:
        subprocess.run(
            [sys.executable, str(cp.with_name('render.py'))],
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
