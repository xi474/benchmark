import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_contract(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    contracts = []
    for cp in sorted(ROOT.rglob("contract.json")):
        if "outputs" in cp.relative_to(ROOT).parts:
            continue
        contracts.append(cp)

    if not contracts:
        raise ValueError("no contracts")

    # Topological order by input dependencies (outputs of other components).
    produced = set()
    remaining = list(contracts)
    while remaining:
        progressed = False
        for cp in list(remaining):
            c = _load_contract(cp)
            deps = [
                p
                for p in c["inputs"]
                if p.startswith("outputs/") and (ROOT / p) not in produced
            ]
            if not deps:
                subprocess.run(
                    [sys.executable, str(cp.with_name("render.py"))],
                    cwd=ROOT,
                    check=True,
                    timeout=60,
                )
                produced.add(ROOT / c["output"])
                remaining.remove(cp)
                progressed = True
        if not progressed:
            raise ValueError("dependency cycle or missing dependency")

    subprocess.run(
        [sys.executable, str(ROOT / "integrate.py")],
        cwd=ROOT,
        check=True,
        timeout=60,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "final_report.py")],
        cwd=ROOT,
        check=True,
        timeout=60,
    )


if __name__ == "__main__":
    main()
