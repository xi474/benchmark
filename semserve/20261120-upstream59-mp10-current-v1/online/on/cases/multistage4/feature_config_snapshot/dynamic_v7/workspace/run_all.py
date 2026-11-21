import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    # Locate all component contracts (excluding outputs).
    contracts = sorted(
        p for p in ROOT.rglob('contract.json')
        if 'outputs' not in p.relative_to(ROOT).parts
    )
    if not contracts:
        raise ValueError('no contracts')

    # Topological order by input dependencies on outputs.
    remaining = list(contracts)
    done = set()
    while remaining:
        progressed = False
        for cp in list(remaining):
            c = __import__('json').loads(cp.read_text(encoding='utf-8'))
            deps = [ROOT / i for i in c.get('inputs', [])]
            if all(
                not str(d).startswith(str(ROOT / 'outputs'))
                or (ROOT / d.relative_to(ROOT)).exists()
                for d in deps
            ):
                subprocess.run(
                    [sys.executable, str(cp.parent / 'render.py')],
                    cwd=ROOT, check=True, timeout=60,
                )
                done.add(cp)
                remaining.remove(cp)
                progressed = True
        if not progressed:
            raise ValueError('dependency cycle or missing dependency')

    # Integrate all component outputs.
    subprocess.run(
        [sys.executable, str(ROOT / 'integrate.py')],
        cwd=ROOT, check=True, timeout=60,
    )


if __name__ == '__main__':
    main()
