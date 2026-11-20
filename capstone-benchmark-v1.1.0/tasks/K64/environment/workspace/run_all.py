from pathlib import Path
from runtime import read, save
from packages.analysis.engine import build_component

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    contract = read(root / "packages/analysis/contract.json")
    result = build_component(root, contract)
    save(root / "outputs/final_report.json", {"task": "K64", "results": {"analysis": result}, "result": result})
