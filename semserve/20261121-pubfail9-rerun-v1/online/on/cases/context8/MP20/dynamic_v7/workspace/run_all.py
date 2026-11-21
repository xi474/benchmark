"""Orchestrate all feature-configuration components from their file contracts.

Locates the workspace root, discovers every component contract, orders the
components by their input/output dependencies, executes each component's
render CLI, and finally runs the integrator and the final report generator.
Every invocation recomputes all outputs; missing dependencies, cycles, or a
failing subcommand cause a non-zero exit.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _discover_contracts():
    """Return a list of (component_dir, contract) for every component."""
    found = []
    for cp in sorted(ROOT.rglob("contract.json")):
        rel = cp.relative_to(ROOT)
        if "outputs" in rel.parts:
            continue
        contract = json.loads(cp.read_text(encoding="utf-8"))
        found.append((cp.parent, contract))
    if not found:
        raise ValueError("no component contracts found")
    return found


def _topological_order(components):
    """Order components so every producer precedes its consumers.

    ``components`` is a list of (component_dir, contract).  A component depends
    on another when one of its input paths equals the other's output path.
    Raises ValueError on a missing dependency or a cycle.
    """
    by_output = {}
    for comp_dir, contract in components:
        out = contract["output"]
        if out in by_output:
            raise ValueError("duplicate output path: %s" % out)
        by_output[out] = (comp_dir, contract)

    # Map each component to the set of components it depends on.
    deps = {}
    for comp_dir, contract in components:
        needed = set()
        for inp in contract["inputs"]:
            if inp in by_output:
                needed.add(by_output[inp][1]["name"])
        deps[contract["name"]] = needed

    names = [c["name"] for _, c in components]
    name_set = set(names)
    for name, needed in deps.items():
        for dep in needed:
            if dep not in name_set:
                raise ValueError("missing dependency %r for %r" % (dep, name))

    ordered = []
    remaining = set(names)
    while remaining:
        ready = sorted(
            n for n in remaining if deps[n].issubset(set(ordered))
        )
        if not ready:
            raise ValueError("dependency cycle among components: %s"
                             % ", ".join(sorted(remaining)))
        ordered.extend(ready)
        remaining.difference_update(ready)

    by_name = {c["name"]: (d, c) for d, c in components}
    return [by_name[n] for n in ordered]


def main():
    components = _discover_contracts()
    ordered = _topological_order(components)

    for comp_dir, contract in ordered:
        render_script = comp_dir / "render.py"
        if not render_script.is_file():
            raise ValueError("missing render script: %s" % render_script)
        subprocess.run(
            [sys.executable, str(render_script)],
            cwd=ROOT,
            check=True,
            timeout=180,
        )

    integrate = ROOT / "integrate.py"
    subprocess.run(
        [sys.executable, str(integrate)],
        cwd=ROOT,
        check=True,
        timeout=180,
    )

    final_report = ROOT / "final_report.py"
    subprocess.run(
        [sys.executable, str(final_report)],
        cwd=ROOT,
        check=True,
        timeout=180,
    )


if __name__ == "__main__":
    main()
