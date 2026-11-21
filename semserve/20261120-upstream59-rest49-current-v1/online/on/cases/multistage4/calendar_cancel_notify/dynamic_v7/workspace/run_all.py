import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    contracts = sorted(
        (p for p in ROOT.rglob("contract.json") if "outputs" not in p.relative_to(ROOT).parts),
        key=lambda p: str(p),
    )
    if not contracts:
        raise ValueError("no contracts")

    produced = set()
    remaining = list(contracts)
    ordered = []
    while remaining:
        progressed = False
        for cp in list(remaining):
            c = json.loads(cp.read_text(encoding="utf-8"))
            deps = [i for i in c["inputs"] if i.startswith("outputs/")]
            if all(d in produced for d in deps):
                ordered.append(cp)
                produced.add(c["output"])
                remaining.remove(cp)
                progressed = True
        if not progressed:
            raise ValueError("dependency cycle or missing dependency")

    for cp in ordered:
        render = cp.with_name("render.py")
        subprocess.run(
            [sys.executable, str(render)],
            cwd=ROOT,
            check=True,
            timeout=60,
        )

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
