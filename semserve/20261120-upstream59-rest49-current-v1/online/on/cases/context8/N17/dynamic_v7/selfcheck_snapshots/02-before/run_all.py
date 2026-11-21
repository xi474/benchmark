"""Implement the project entry point using the published business contracts."""
from pathlib import Path
import json

from runtime import read, module


def main():
    root = Path(__file__).resolve().parent

    # Load contracts.
    td_contract = read(root / "engines/template_dependencies/contract.json")
    su_contract = read(root / "engines/stylesheet_updates/contract.json")
    ri_contract = read(root / "engines/reverse_index/contract.json")

    td_mod = module(root, "engines/template_dependencies/engine.py")
    su_mod = module(root, "engines/stylesheet_updates/engine.py")
    ri_mod = module(root, "engines/reverse_index/engine.py")

    td_result = td_mod.build_component(root, td_contract)
    ri_result = ri_mod.build_component(root, ri_contract)
    su_result = su_mod.build_component(root, su_contract)

    results = {
        "template_dependencies": td_result,
        "stylesheet_updates": su_result,
        "reverse_index": ri_result,
    }

    delivery = read(root / "delivery.json")
    result_file = read(root / delivery["result_file"])

    report = {
        "task": "N17",
        "results": results,
        "result": result_file,
    }

    out = root / "outputs/final_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
