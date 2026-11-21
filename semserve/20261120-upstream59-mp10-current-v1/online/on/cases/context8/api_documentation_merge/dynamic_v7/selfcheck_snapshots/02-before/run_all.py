import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_contracts():
    contracts = {}
    for cp in sorted(ROOT.rglob('contract.json')):
        rel = cp.relative_to(ROOT)
        if 'outputs' in rel.parts:
            continue
        c = json.loads(cp.read_text(encoding='utf-8'))
        contracts[c['name']] = (cp, c)
    return contracts


def _topo_order(contracts):
    # Map output path -> component name that produces it.
    producer = {}
    for name, (cp, c) in contracts.items():
        producer[c['output']] = name

    # Build dependency edges: component depends on components producing its inputs.
    deps = {}
    for name, (cp, c) in contracts.items():
        d = set()
        for inp in c['inputs']:
            if inp in producer:
                d.add(producer[inp])
        deps[name] = d

    order = []
    visited = set()
    visiting = set()

    def visit(name):
        if name in visited:
            return
        if name in visiting:
            raise ValueError('circular dependency: %s' % name)
        visiting.add(name)
        for dep in sorted(deps[name]):
            if dep not in contracts:
                raise ValueError('missing dependency: %s' % dep)
            visit(dep)
        visiting.remove(name)
        visited.add(name)
        order.append(name)

    for name in sorted(contracts):
        visit(name)
    return order


def main():
    contracts = _load_contracts()
    if not contracts:
        raise ValueError('no contracts')

    order = _topo_order(contracts)

    for name in order:
        cp, c = contracts[name]
        render = cp.with_name('render.py')
        if not render.is_file():
            raise ValueError('missing render.py for %s' % name)
        subprocess.run([sys.executable, str(render)], cwd=ROOT, check=True)

    # Run the integrator to produce core_manifest.json.
    integrate = ROOT / 'integrate.py'
    subprocess.run([sys.executable, str(integrate)], cwd=ROOT, check=True)

    # Run the final report generator.
    final_report = ROOT / 'final_report.py'
    subprocess.run([sys.executable, str(final_report)], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
