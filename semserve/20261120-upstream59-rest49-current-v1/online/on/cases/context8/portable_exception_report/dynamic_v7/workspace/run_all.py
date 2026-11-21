import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    contracts = [
        x for x in ROOT.rglob('contract.json')
        if 'outputs' not in x.relative_to(ROOT).parts
    ]
    if not contracts:
        raise ValueError('no contracts')
    # Topological order: report depends on chain and frames outputs.
    ordered = sorted(contracts, key=lambda cp: len(cp.relative_to(ROOT).parts))
    for cp in ordered:
        subprocess.run(
            [sys.executable, str(cp.with_name('render.py')), str(cp)],
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
