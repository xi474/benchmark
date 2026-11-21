import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_contract(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _topological_order(contracts):
    """Return contracts in dependency order; raise on missing deps or cycles."""
    by_name = {}
    for cp in contracts:
        c = _load_contract(cp)
        name = c["name"]
        if name in by_name:
            raise ValueError("duplicate component name: %s" % name)
        by_name[name] = (cp, c)

    # Map output path -> producing component name.
    producer = {}
    for name, (cp, c) in by_name.items():
        out = c["output"]
        if out in producer:
            raise ValueError("duplicate output path: %s" % out)
        producer[out] = name

    # Build dependency edges: component depends on components producing its inputs.
    deps = {}
    for name, (cp, c) in by_name.items():
        d = set()
        for inp in c["inputs"]:
            if inp in producer:
                d.add(producer[inp])
            else:
                # Input not produced by any component must already exist as a file.
                if not (ROOT / inp).is_file():
                    raise ValueError("missing input: %s" % inp)
        deps[name] = d

    # Kahn's algorithm.
    order = []
    remaining = set(by_name)
    while remaining:
        ready = [n for n in remaining if deps[n] <= set(order)]
        if not ready:
            raise ValueError("dependency cycle detected")
        ready.sort()
        for n in ready:
            order.append(n)
            remaining.discard(n)

    return [by_name[n] for n in order]


def main():
    contracts = [
        x
        for x in ROOT.rglob("contract.json")
        if "outputs" not in x.relative_to(ROOT).parts
    ]
    if not contracts:
        raise ValueError("no contracts")

    ordered = _topological_order(contracts)

    for cp, c in ordered:
        render = cp.with_name("render.py")
        if not render.is_file():
            raise ValueError("missing render.py for %s" % c["name"])
        subprocess.run(
            [sys.executable, str(render)],
            cwd=ROOT,
            check=True,
            timeout=180,
        )

    # Run the integrator to produce core_manifest.json.
    integrate = ROOT / "integrate.py"
    subprocess.run(
        [sys.executable, str(integrate)],
        cwd=ROOT,
        check=True,
        timeout=180,
    )

    # Run the final report generator.
    final_report = ROOT / "final_report.py"
    subprocess.run(
        [sys.executable, str(final_report)],
        cwd=ROOT,
        check=True,
        timeout=180,
    )


if __name__ == "__main__":
    main()
