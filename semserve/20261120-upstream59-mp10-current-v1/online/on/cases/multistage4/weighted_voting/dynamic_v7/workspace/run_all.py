import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_contracts():
    contracts = {}
    for cp in sorted(ROOT.rglob("contract.json")):
        rel = cp.relative_to(ROOT)
        if "outputs" in rel.parts:
            continue
        c = json.loads(cp.read_text(encoding="utf-8"))
        name = c["name"]
        if name in contracts:
            raise ValueError("duplicate component name: %s" % name)
        contracts[name] = (cp, c)
    if not contracts:
        raise ValueError("no contracts found")
    return contracts


def _topological_order(contracts):
    # Build dependency graph from input files that are outputs of other components.
    name_by_output = {}
    for name, (cp, c) in contracts.items():
        out = c["output"]
        if out in name_by_output:
            raise ValueError("duplicate output path: %s" % out)
        name_by_output[out] = name

    deps = {}
    for name, (cp, c) in contracts.items():
        d = set()
        for inp in c["inputs"]:
            if inp in name_by_output:
                d.add(name_by_output[inp])
        deps[name] = d

    # Kahn's algorithm; detect cycles.
    order = []
    remaining = set(contracts)
    while remaining:
        ready = [n for n in remaining if deps[n] <= set(order)]
        if not ready:
            raise ValueError("dependency cycle detected among components")
        ready.sort()
        for n in ready:
            order.append(n)
            remaining.discard(n)
    return order


def main():
    contracts = _load_contracts()
    order = _topological_order(contracts)

    for name in order:
        cp, c = contracts[name]
        render_py = cp.with_name("render.py")
        if not render_py.is_file():
            raise ValueError("missing render.py for component %s" % name)
        proc = subprocess.run(
            [sys.executable, str(render_py)],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "component %s failed with exit code %d" % (name, proc.returncode)
            )

    # Run the integrator to produce core_manifest.json.
    integrate_py = ROOT / "integrate.py"
    if not integrate_py.is_file():
        raise ValueError("missing integrate.py")
    proc = subprocess.run(
        [sys.executable, str(integrate_py)],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("integrate.py failed with exit code %d" % proc.returncode)


if __name__ == "__main__":
    main()
