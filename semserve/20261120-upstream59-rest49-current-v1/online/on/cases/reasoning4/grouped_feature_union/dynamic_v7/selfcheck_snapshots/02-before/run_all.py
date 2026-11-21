import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_contracts():
    contracts = {}
    for cp in sorted(ROOT.rglob("contract.json")):
        if "outputs" in cp.relative_to(ROOT).parts:
            continue
        c = json.loads(cp.read_text(encoding="utf-8"))
        name = c["name"]
        if name in contracts:
            raise ValueError("duplicate component name: %s" % name)
        contracts[name] = {"contract": c, "dir": cp.parent}
    return contracts


def _topological_order(contracts):
    producer = {}
    for name, info in contracts.items():
        out = info["contract"]["output"]
        if out in producer:
            raise ValueError("duplicate output path: %s" % out)
        producer[out] = name

    deps = {}
    for name, info in contracts.items():
        d = set()
        for inp in info["contract"]["inputs"]:
            if inp in producer:
                d.add(producer[inp])
        deps[name] = d

    order = []
    visited = set()
    visiting = set()

    def visit(name):
        if name in visited:
            return
        if name in visiting:
            raise ValueError("dependency cycle detected at %s" % name)
        visiting.add(name)
        for dep in sorted(deps[name]):
            visit(dep)
        visiting.remove(name)
        visited.add(name)
        order.append(name)

    for name in sorted(contracts):
        visit(name)

    return order


def main():
    contracts = _load_contracts()
    if not contracts:
        raise ValueError("no contracts")

    order = _topological_order(contracts)

    for name in order:
        info = contracts[name]
        render = info["dir"] / "render.py"
        if not render.is_file():
            raise ValueError("missing render.py for %s" % name)
        subprocess.run(
            [sys.executable, str(render)],
            cwd=ROOT,
            check=True,
            timeout=180,
        )

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
