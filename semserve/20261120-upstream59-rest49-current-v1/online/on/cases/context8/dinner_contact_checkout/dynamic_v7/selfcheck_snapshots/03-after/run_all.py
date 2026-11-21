import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")


def main():
    contracts = sorted(
        p for p in ROOT.rglob("contract.json")
        if "outputs" not in p.relative_to(ROOT).parts
    )
    if not contracts:
        raise ValueError("no contracts")

    # Topologically order components by their input dependencies on other
    # component outputs, then run each component's render.py CLI.
    names = {}
    for cp in contracts:
        c = json.loads(cp.read_text(encoding="utf-8"))
        names[c["name"]] = cp

    # Build dependency graph: component A depends on B if A's inputs reference
    # B's output file.
    deps = {}
    for name, cp in names.items():
        c = json.loads(cp.read_text(encoding="utf-8"))
        deps[name] = []
        for inp in c["inputs"]:
            for other_name, other_cp in names.items():
                if other_name == name:
                    continue
                oc = json.loads(other_cp.read_text(encoding="utf-8"))
                if inp == oc["output"]:
                    deps[name].append(other_name)

    # Topological sort (Kahn's algorithm), detect cycles.
    indeg = {n: len(deps[n]) for n in names}
    from collections import deque
    ready = deque(sorted(n for n in names if indeg[n] == 0))
    order = []
    while ready:
        n = ready.popleft()
        order.append(n)
        for m in names:
            if n in deps[m]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    ready.append(m)
    if len(order) != len(names):
        raise ValueError("dependency cycle detected")

    for name in order:
        cp = names[name]
        subprocess.run(
            [sys.executable, str(cp.with_name("render.py"))],
            cwd=ROOT,
            check=True,
            timeout=60,
        )

    # Run the integrator to produce core_manifest.json.
    subprocess.run(
        [sys.executable, str(ROOT / "integrate.py")],
        cwd=ROOT,
        check=True,
        timeout=60,
    )

    # Run the final report generator.
    subprocess.run(
        [sys.executable, str(ROOT / "final_report.py")],
        cwd=ROOT,
        check=True,
        timeout=60,
    )


if __name__ == "__main__":
    main()
