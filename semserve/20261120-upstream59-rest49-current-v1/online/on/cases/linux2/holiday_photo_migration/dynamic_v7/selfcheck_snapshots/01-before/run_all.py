import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    contracts = sorted(ROOT.rglob('contract.json'))
    contracts = [c for c in contracts if 'outputs' not in c.relative_to(ROOT).parts]
    if not contracts:
        raise ValueError('no contracts')

    # Topological order by dependency: run components whose inputs are all
    # produced by already-run components or are static inputs.
    remaining = list(contracts)
    done = set()
    while remaining:
        progressed = False
        for cp in list(remaining):
            import json
            c = json.loads(cp.read_text(encoding='utf-8'))
            deps = [ROOT / p for p in c['inputs']]
            # A dependency is satisfied if it is a static input (not under
            # outputs/) or its producing component has already run.
            satisfied = True
            for d in deps:
                rel = d.relative_to(ROOT)
                if 'outputs' in rel.parts:
                    # find the contract that produces this output
                    producer = None
                    for other in contracts:
                        oc = json.loads(other.read_text(encoding='utf-8'))
                        if (ROOT / oc['output']).resolve() == d.resolve():
                            producer = oc['name']
                            break
                    if producer is None or producer not in done:
                        satisfied = False
                        break
            if satisfied:
                subprocess.run(
                    [sys.executable, str(cp.with_name('render.py'))],
                    cwd=ROOT, check=True, timeout=60,
                )
                done.add(c['name'])
                remaining.remove(cp)
                progressed = True
        if not progressed:
            raise ValueError('dependency cycle or missing dependency')

    subprocess.run([sys.executable, str(ROOT / 'integrate.py')],
                   cwd=ROOT, check=True, timeout=60)
    subprocess.run([sys.executable, str(ROOT / 'final_report.py')],
                   cwd=ROOT, check=True, timeout=60)


if __name__ == '__main__':
    main()
