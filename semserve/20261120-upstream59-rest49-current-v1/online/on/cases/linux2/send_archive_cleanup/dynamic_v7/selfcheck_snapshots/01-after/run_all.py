import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    contracts = sorted(
        p for p in ROOT.rglob("contract.json")
        if "outputs" not in p.relative_to(ROOT).parts
    )
    if not contracts:
        raise SystemExit("no contracts found")

    # Run each component's render.py in dependency order (topological by inputs).
    done = set()
    while len(done) < len(contracts):
        progressed = False
        for cp in contracts:
            if cp in done:
                continue
            import json
            c = json.loads(cp.read_text(encoding="utf-8"))
            inputs = [ROOT / p for p in c["inputs"]]
            if all(p.exists() for p in inputs):
                subprocess.run(
                    [sys.executable, str(cp.with_name("render.py"))],
                    cwd=ROOT, check=True, timeout=60,
                )
                done.add(cp)
                progressed = True
        if not progressed:
            raise SystemExit("dependency cycle or missing input")

    subprocess.run(
        [sys.executable, str(ROOT / "integrate.py")],
        cwd=ROOT, check=True, timeout=60,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "final_report.py")],
        cwd=ROOT, check=True, timeout=60,
    )


if __name__ == "__main__":
    main()
