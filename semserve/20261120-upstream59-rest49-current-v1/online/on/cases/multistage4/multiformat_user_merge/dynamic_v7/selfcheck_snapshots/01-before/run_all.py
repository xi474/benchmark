import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _contracts():
    contracts = []
    for cp in sorted(ROOT.rglob('contract.json')):
        if 'outputs' in cp.relative_to(ROOT).parts:
            continue
        contracts.append(cp)
    return contracts


def main():
    contracts = _contracts()
    name_to_contract = {}
    for cp in contracts:
        c = json.loads(cp.read_text(encoding='utf-8'))
        name_to_contract[c['name']] = (cp, c)

    deps = {}
    for name, (cp, c) in name_to_contract.items():
        d = set()
        for inp in c['inputs']:
            for other_name, (ocp, oc) in name_to_contract.items():
                if oc['output'] == inp:
                    d.add(other_name)
        deps[name] = d

    visiting = set()
    visited = set()

    def visit(name, stack):
        if name in visiting:
            raise ValueError('cycle detected: ' + ' -> '.join(stack + [name]))
        if name in visited:
            return
        visiting.add(name)
        for dep in deps[name]:
            visit(dep, stack + [name])
        visiting.remove(name)
        visited.add(name)

    for name in name_to_contract:
        visit(name, [])

    order = []
    remaining = set(name_to_contract)
    while remaining:
        ready = [n for n in remaining if deps[n] <= (set(name_to_contract) - remaining)]
        if not ready:
            raise ValueError('unresolved dependencies')
        for n in sorted(ready):
            order.append(n)
            remaining.remove(n)

    for name in order:
        cp, c = name_to_contract[name]
        render = cp.with_name('render.py')
        subprocess.run([sys.executable, str(render), str(ROOT), str(cp)],
                       cwd=ROOT, check=True)

    subprocess.run([sys.executable, str(ROOT / 'integrate.py')],
                   cwd=ROOT, check=True)

    subprocess.run([sys.executable, str(ROOT / 'final_report.py')],
                   cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
