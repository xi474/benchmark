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


def _topo_order(contracts):
    names = set(contracts)
    output_to_name = {}
    for name, (cp, c) in contracts.items():
        out = c['output']
        if out in output_to_name:
            raise ValueError('duplicate output path: %s' % out)
        output_to_name[out] = name

    deps = {}
    for name, (cp, c) in contracts.items():
        d = set()
        for inp in c['inputs']:
            if inp in output_to_name:
                dep = output_to_name[inp]
                if dep == name:
                    raise ValueError('self-dependency: %s' % name)
                d.add(dep)
        deps[name] = d

    result = []
    remaining = dict(deps)
    while remaining:
        ready = [n for n, d in remaining.items() if not d]
        if not ready:
            raise ValueError('dependency cycle detected')
        ready.sort()
        for n in ready:
            result.append(n)
            del remaining[n]
        for n in list(remaining):
            remaining[n] = remaining[n] - set(ready)
    return result


def main():
    contracts = _load_contracts()
    if not contracts:
        raise ValueError('no contracts found')
    order = _topo_order(contracts)
    for name in order:
        cp, c = contracts[name]
        render = cp.with_name('render.py')
        if not render.is_file():
            raise ValueError('missing render.py for %s' % name)
        subprocess.run([sys.executable, str(render), str(cp)], cwd=ROOT, check=True)
    integrate = ROOT / 'integrate.py'
    if not integrate.is_file():
        raise ValueError('missing integrate.py')
    subprocess.run([sys.executable, str(integrate)], cwd=ROOT, check=True)
    final_report = ROOT / 'final_report.py'
    if not final_report.is_file():
        raise ValueError('missing final_report.py')
    subprocess.run([sys.executable, str(final_report)], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
