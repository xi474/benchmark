import json
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
        raise ValueError("no contracts")

    # Topological order by dependency: a component depends on another if its
    # input path equals the other's output path.
    by_name = {}
    for cp in contracts:
        c = json.loads(cp.read_text(encoding="utf-8"))
        by_name[c["name"]] = (cp, c)

    deps = {}
    for name, (cp, c) in by_name.items():
        d = set()
        for inp in c["inputs"]:
            for other_name, (ocp, oc) in by_name.items():
                if other_name != name and inp == oc["output"]:
                    d.add(other_name)
        deps[name] = d

    # Detect cycles.
    order = []
    remaining = set(by_name)
    while remaining:
        ready = [n for n in remaining if deps[n] <= set(order)]
        if not ready:
            raise ValueError("dependency cycle detected")
        ready.sort()
        for n in ready:
            remaining.remove(n)
            order.append(n)

    for name in order:
        cp, c = by_name[name]
        subprocess.run(
            [sys.executable, str(cp.with_name("render.py"))],
            cwd=ROOT,
            check=True,
        )

    subprocess.run(
        [sys.executable, str(ROOT / "integrate.py")],
        cwd=ROOT,
        check=True,
    )

    subprocess.run(
        [sys.executable, str(ROOT / "final_report.py")],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
