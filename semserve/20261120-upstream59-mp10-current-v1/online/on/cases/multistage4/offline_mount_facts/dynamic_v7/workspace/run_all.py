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
        contracts[c["name"]] = {"path": cp, "contract": c}
    return contracts


def _topo_order(contracts):
    producer = {}
    for name, info in contracts.items():
        out = info["contract"]["output"]
        if out in producer:
            raise ValueError("duplicate output %r" % out)
        producer[out] = name

    deps = {}
    for name, info in contracts.items():
        d = set()
        for inp in info["contract"]["inputs"]:
            if inp in producer:
                d.add(producer[inp])
        deps[name] = d

    order = []
    remaining = set(contracts)
    while remaining:
        ready = [n for n in remaining if deps[n] <= set(order)]
        if not ready:
            raise ValueError("dependency cycle or missing dependency")
        ready.sort()
        for n in ready:
            order.append(n)
            remaining.discard(n)
    return order


def main():
    contracts = _load_contracts()
    if not contracts:
        raise ValueError("no contracts")
    order = _topo_order(contracts)
    for name in order:
        info = contracts[name]
        cp = info["path"]
        subprocess.run(
            [sys.executable, str(cp.with_name("render.py"))],
            cwd=ROOT,
            check=True,
        )
    subprocess.run([sys.executable, str(ROOT / "integrate.py")], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(ROOT / "final_report.py")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
