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

EXTRA = {'workers': [{'id': 'w1', 'capacity': 1, 'skills': ['x', 'y']}, {'id': 'w2', 'capacity': 2, 'skills': ['x', 'z']}, {'id': 'w3', 'capacity': 1, 'skills': ['y', 'z']}], 'items': [{'id': 'i1', 'requires': ['x']}, {'id': 'i2', 'requires': ['y']}, {'id': 'i3', 'requires': ['z']}], 'candidates': [{'item': 'i1', 'worker': 'w1', 'score': 9, 'cost': 5}, {'item': 'i1', 'worker': 'w2', 'score': 8, 'cost': 2}, {'item': 'i2', 'worker': 'w1', 'score': 8, 'cost': 2}, {'item': 'i2', 'worker': 'w3', 'score': 7, 'cost': 1}, {'item': 'i3', 'worker': 'w2', 'score': 8, 'cost': 3}, {'item': 'i3', 'worker': 'w3', 'score': 9, 'cost': 6}]}
EXPECTED_EXTRA = {'algorithm': 'constrained_assignment', 'assignments': [{'item': 'i1', 'worker': 'w2', 'score': 8, 'cost': 2}, {'item': 'i2', 'worker': 'w1', 'score': 8, 'cost': 2}, {'item': 'i3', 'worker': 'w3', 'score': 9, 'cost': 6}], 'total_score': 25, 'total_cost': 10}
EXPECTED_ACTUAL = {'algorithm': 'constrained_assignment', 'assignments': [{'item': 'api', 'worker': 'zoe', 'score': 8, 'cost': 5}, {'item': 'backfill', 'worker': 'xavier', 'score': 13, 'cost': 6}, {'item': 'ddl', 'worker': 'wen', 'score': 13, 'cost': 4}, {'item': 'rollback', 'worker': 'yara', 'score': 10, 'cost': 5}], 'total_score': 44, 'total_cost': 20}

def main() -> None:
    payload = load_payload(ROOT / "inputs" / "validator_assignment.json")
    assert solve(EXTRA) == EXPECTED_EXTRA
    assert solve(payload) == EXPECTED_ACTUAL
    assert run(ROOT / "inputs" / "validator_assignment.json", HERE / "contract.json") == EXPECTED_ACTUAL
    written = json.loads((ROOT / "outputs" / "validator_assignment.json").read_text(encoding="utf-8"))
    assert written == EXPECTED_ACTUAL
    print("PASS validator_assignment")

if __name__ == "__main__":
    main()
