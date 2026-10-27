from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAMES = ['maintenance_windows', 'maintainer_assignment', 'upgrade_order']

def main() -> None:
    for name in NAMES:
        proc = subprocess.run([sys.executable, "check_module.py"], cwd=ROOT / "engines" / name, capture_output=True, text=True)
        if proc.returncode:
            raise AssertionError(f"{name} failed: {proc.stdout}{proc.stderr}")
    proc = subprocess.run([sys.executable, "integrate.py"], cwd=ROOT, capture_output=True, text=True)
    if proc.returncode:
        raise AssertionError(proc.stdout + proc.stderr)
    report = json.loads((ROOT / "outputs" / "final_report.json").read_text(encoding="utf-8"))
    assert report["title"] == 'Dependency release reasoner'
    assert report["solver_count"] == 3
    assert sorted(report["engines"]) == sorted(NAMES)
    for name in NAMES:
        assert report["engines"][name]["result"] == json.loads((ROOT / "outputs" / f"{name}.json").read_text(encoding="utf-8"))
    print("PASS dependency_release_reasoner")

if __name__ == "__main__":
    main()
