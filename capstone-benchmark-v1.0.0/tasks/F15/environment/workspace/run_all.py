from pathlib import Path
from runtime import read, save
from engines.analysis.engine import build_component

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    contract = read(root / "engines/analysis/contract.json")
    result = build_component(root, contract)
    save(root / "outputs/final_report.json", {"task": "F15", "results": {"analysis": result}, "result": result})
