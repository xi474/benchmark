from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from model import load_payload
from solver import solve
from render import run

EXTRA = {'nodes': [{'id': 'a', 'duration': 3, 'requires': []}, {'id': 'b', 'duration': 5, 'requires': []}, {'id': 'c', 'duration': 4, 'requires': ['a']}, {'id': 'd', 'duration': 2, 'requires': ['a', 'b']}, {'id': 'e', 'duration': 6, 'requires': ['c', 'd']}]}
EXPECTED_EXTRA = {'algorithm': 'dependency_batches', 'batches': [['a', 'b'], ['c', 'd'], ['e']], 'critical_path': ['a', 'c', 'e'], 'critical_duration': 13}
EXPECTED_ACTUAL = {'algorithm': 'dependency_batches', 'batches': [['lockfile'], ['corelib', 'database'], ['adapter'], ['gateway', 'worker'], ['integration'], ['publish']], 'critical_path': ['lockfile', 'corelib', 'adapter', 'gateway', 'integration', 'publish'], 'critical_duration': 32}

def main() -> None:
    payload = load_payload(ROOT / "inputs" / "upgrade_order.json")
    assert solve(EXTRA) == EXPECTED_EXTRA
    assert solve(payload) == EXPECTED_ACTUAL
    assert run(ROOT / "inputs" / "upgrade_order.json", HERE / "contract.json") == EXPECTED_ACTUAL
    written = json.loads((ROOT / "outputs" / "upgrade_order.json").read_text(encoding="utf-8"))
    assert written == EXPECTED_ACTUAL
    print("PASS upgrade_order")

if __name__ == "__main__":
    main()
