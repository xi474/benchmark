"""Implement the project entry point using the published business contracts."""
import json
from pathlib import Path

from runtime import read, module


def main():
    root = Path(__file__).resolve().parent
    delivery = read(root / "delivery.json")

    # Load component contracts and engines.
    components = {}
    for name, out_path in delivery["component_outputs"].items():
        comp_dir = root / "products" / name
        contract = read(comp_dir / "contract.json")
        engine = module(comp_dir, "engine.py")
        components[name] = (contract, engine, out_path)

    # object_scan first (no dependencies).
    scan_contract, scan_engine, scan_out = components["object_scan"]
    scan_value = scan_engine.build_component(root, scan_contract)

    # cleaned_repo depends on scan.
    clean_contract, clean_engine, clean_out = components["cleaned_repo"]
    clean_value = clean_engine.build_component(root, clean_contract)

    # recovery_report depends on scan and cleaned.
    report_contract, report_engine, report_out = components["recovery_report"]
    report_value = report_engine.build_component(root, report_contract)

    results = {
        "object_scan": scan_value,
        "cleaned_repo": clean_value,
        "recovery_report": report_value,
    }

    final = {
        "task": delivery["task"],
        "results": results,
        "result": report_value,
    }

    out = root / delivery["report"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(final, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
