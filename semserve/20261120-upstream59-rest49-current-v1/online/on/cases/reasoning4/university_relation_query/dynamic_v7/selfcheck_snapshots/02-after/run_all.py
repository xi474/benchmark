import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    contracts = sorted(ROOT.rglob("contract.json"))
    contracts = [c for c in contracts if "outputs" not in c.relative_to(ROOT).parts]
    if not contracts:
        raise ValueError("no contracts")

    # Topological order by input dependency on outputs.
    produced = set()
    remaining = list(contracts)
    while remaining:
        progressed = False
        for cp in list(remaining):
            c = json.loads(cp.read_text(encoding="utf-8"))
            deps = [p for p in c["inputs"] if p.startswith("outputs/")]
            if all(d in produced for d in deps):
                subprocess.run(
                    [sys.executable, str(cp.with_name("render.py")), str(ROOT), str(cp)],
                    cwd=ROOT,
                    check=True,
                )
                produced.add(c["output"])
                remaining.remove(cp)
                progressed = True
        if not progressed:
            raise ValueError("dependency cycle or missing dependency")

    subprocess.run([sys.executable, str(ROOT / "integrate.py")], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(ROOT / "final_report.py")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
