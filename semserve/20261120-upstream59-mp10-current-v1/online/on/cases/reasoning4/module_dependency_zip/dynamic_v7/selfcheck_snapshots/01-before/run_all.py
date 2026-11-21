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
    names = set(contracts)
    order = []
    visited = set()
    visiting = set()

    def visit(name):
        if name in visited:
            return
        if name in visiting:
            raise ValueError('cycle in component dependencies: %s' % name)
        visiting.add(name)
        cp, c = contracts[name]
        for inp in c.get('inputs', []):
            for other_name, (ocp, oc) in contracts.items():
                if inp == oc.get('output'):
                    visit(other_name)
        visiting.remove(name)
        visited.add(name)
        order.append(name)

    for name in names:
        visit(name)
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
            [sys.executable, str(render)],
            cwd=ROOT,
            check=True,
            timeout=60,
        )
    subprocess.run(
        [sys.executable, str(ROOT / 'integrate.py')],
        cwd=ROOT,
        check=True,
        timeout=60,
    )
    subprocess.run(
        [sys.executable, str(ROOT / 'final_report.py')],
        cwd=ROOT,
        check=True,
        timeout=60,
    )


if __name__ == '__main__':
    main()
