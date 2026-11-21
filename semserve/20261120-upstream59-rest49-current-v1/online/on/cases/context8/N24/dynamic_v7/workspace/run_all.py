"""Implement the project entry point using the published business contracts."""
import json
from pathlib import Path

from runtime import module, read

ROOT = Path(__file__).resolve().parent


def main():
    delivery = read(ROOT / "delivery.json")

    # Build components in dependency order: parsers first, then settlement.
    order = ["accounts", "books", "orders", "settlement"]
    results = {}
    for name in order:
        contract = read(ROOT / "products" / name / "contract.json")
        engine = module(ROOT / "products" / name, "engine.py")
        results[name] = engine.build_component(ROOT, contract)

    result_file = delivery["result_file"]
    result = read(ROOT / result_file)

    report = {
        "task": delivery["task"],
        "results": results,
        "result": result,
    }
    out = ROOT / delivery["report"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
