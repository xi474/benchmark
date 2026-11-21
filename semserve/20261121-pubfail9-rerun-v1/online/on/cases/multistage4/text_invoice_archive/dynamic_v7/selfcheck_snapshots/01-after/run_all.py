import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _contracts():
    result = []
    for cp in sorted(ROOT.rglob('contract.json')):
        rel = cp.relative_to(ROOT)
        if 'outputs' in rel.parts:
            continue
        result.append(cp)
    return result


def main():
    contracts = _contracts()
    if not contracts:
        raise ValueError('no contracts')

    produced = {}
    for cp in contracts:
        c = json.loads(cp.read_text(encoding='utf-8'))
        produced[c['name']] = cp

    remaining = list(contracts)
    done = set()
    while remaining:
        progressed = False
        for cp in list(remaining):
            c = json.loads(cp.read_text(encoding='utf-8'))
            deps = []
            for inp in c['inputs']:
                for name, producer in produced.items():
                    if name == c['name']:
                        continue
                    pc = json.loads(producer.read_text(encoding='utf-8'))
                    if pc['output'] == inp:
                        deps.append(name)
            if all(d in done for d in deps):
                subprocess.run(
                    [sys.executable, str(cp.with_name('render.py')), str(cp)],
                    cwd=ROOT, check=True, timeout=180,
                )
                done.add(c['name'])
                remaining.remove(cp)
                progressed = True
        if not progressed:
            raise ValueError('dependency cycle or missing dependency')

    subprocess.run(
        [sys.executable, str(ROOT / 'integrate.py')],
        cwd=ROOT, check=True, timeout=180,
    )
    subprocess.run(
        [sys.executable, str(ROOT / 'final_report.py')],
        cwd=ROOT, check=True, timeout=180,
    )


if __name__ == '__main__':
    main()
