from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAMES = ['change_windows', 'validator_assignment', 'migration_order']

def main() -> None:
    engines = {}
    for name in NAMES:
        path = ROOT / "outputs" / f"{name}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        engines[name] = {"algorithm": payload["algorithm"], "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "result": payload}
    report = {"title": 'Schema evolution reasoner', "solver_count": len(engines), "engines": engines}
    target = ROOT / "outputs" / "final_report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(target)

if __name__ == "__main__":
    main()
