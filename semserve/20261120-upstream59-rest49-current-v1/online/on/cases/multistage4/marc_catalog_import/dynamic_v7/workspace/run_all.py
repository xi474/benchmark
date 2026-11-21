import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    contracts = []
    for cp in sorted(ROOT.rglob("contract.json")):
        if "outputs" in cp.relative_to(ROOT).parts:
            continue
        contracts.append(cp)

    # Topological order by input dependency among component outputs.
    outputs = {c["output"] for c in [json.loads(cp.read_text(encoding="utf-8")) for cp in contracts]}
    remaining = list(contracts)
    done = set()
    while remaining:
        progressed = False
        for cp in list(remaining):
            c = json.loads(cp.read_text(encoding="utf-8"))
            deps = [p for p in c["inputs"] if p in outputs]
            if all(d in done for d in deps):
                subprocess.run(
                    [sys.executable, str(cp.with_name("render.py"))],
                    cwd=ROOT,
                    check=True,
                    timeout=60,
                )
                done.add(c["output"])
                remaining.remove(cp)
                progressed = True
        if not progressed:
            raise RuntimeError("dependency cycle or missing dependency")

    subprocess.run([sys.executable, str(ROOT / "integrate.py")], cwd=ROOT, check=True, timeout=60)
    subprocess.run([sys.executable, str(ROOT / "final_report.py")], cwd=ROOT, check=True, timeout=60)


if __name__ == "__main__":
    main()
