"""Implement the project entry point using the published business contracts."""
from pathlib import Path
import json
from runtime import read, module

ROOT = Path(__file__).resolve().parent


def main():
    delivery = read(ROOT / "delivery.json")
    components = {}
    # block_layout must run first: squared and cubed bind to its output.
    order = ["block_layout", "squared", "cubed"]
    for name in order:
        contract = read(ROOT / "engines" / name / "contract.json")
        engine = module(ROOT, f"engines/{name}/engine.py")
        value = engine.build_component(ROOT, contract)
        components[name] = value
    result = read(ROOT / delivery["result_file"])
    report = {
        "task": "N11",
        "results": components,
        "result": result,
    }
    out = ROOT / delivery["report"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
