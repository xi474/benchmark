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

EXTRA = {'items': [{'id': 'a', 'start': 0, 'end': 3, 'value': 6}, {'id': 'b', 'start': 1, 'end': 4, 'value': 7}, {'id': 'c', 'start': 3, 'end': 5, 'value': 5}, {'id': 'd', 'start': 5, 'end': 7, 'value': 4}, {'id': 'e', 'start': 4, 'end': 8, 'value': 10}]}
EXPECTED_EXTRA = {'algorithm': 'weighted_selection', 'selected_ids': ['b', 'e'], 'total_value': 17}
EXPECTED_ACTUAL = {'algorithm': 'weighted_selection', 'selected_ids': ['core', 'plugin', 'storage'], 'total_value': 35}

def main() -> None:
    payload = load_payload(ROOT / "inputs" / "maintenance_windows.json")
    assert solve(EXTRA) == EXPECTED_EXTRA
    assert solve(payload) == EXPECTED_ACTUAL
    assert run(ROOT / "inputs" / "maintenance_windows.json", HERE / "contract.json") == EXPECTED_ACTUAL
    written = json.loads((ROOT / "outputs" / "maintenance_windows.json").read_text(encoding="utf-8"))
    assert written == EXPECTED_ACTUAL
    print("PASS maintenance_windows")

if __name__ == "__main__":
    main()
