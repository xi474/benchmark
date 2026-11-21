import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    contracts = [
        cp
        for cp in sorted(ROOT.rglob("contract.json"))
        if "outputs" not in cp.relative_to(ROOT).parts
    ]
    if not contracts:
        raise ValueError("no contracts")

    produced_outputs = {
        ROOT / json.loads(cp.read_text(encoding="utf-8"))["output"]
        for cp in contracts
    }

    produced = set()
    remaining = list(contracts)
    while remaining:
        progressed = False
        for cp in list(remaining):
            c = json.loads(cp.read_text(encoding="utf-8"))
            ready = True
            for inp in c["inputs"]:
                p = ROOT / inp
                if p in produced_outputs and p not in produced:
                    ready = False
                    break
                if not p.is_file():
                    raise ValueError("missing input: " + inp)
            if not ready:
                continue
            subprocess.run(
                [sys.executable, str(cp.with_name("render.py"))],
                cwd=ROOT,
                check=True,
                timeout=180,
            )
            produced.add(ROOT / c["output"])
            remaining.remove(cp)
            progressed = True
        if not progressed:
            raise ValueError("dependency cycle or missing input")

    subprocess.run(
        [sys.executable, str(ROOT / "integrate.py")],
        cwd=ROOT,
        check=True,
        timeout=180,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "final_report.py")],
        cwd=ROOT,
        check=True,
        timeout=180,
    )


if __name__ == "__main__":
    main()
