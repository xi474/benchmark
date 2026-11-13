import subprocess
import sys
from pathlib import Path
from runtime import read
from comparison import check_value

root = Path(__file__).resolve().parent
subprocess.run([sys.executable, str(root / "run_all.py")], cwd=root, check=True)
expected = read(root / "public_expected.json")
report = read(root / "outputs/final_report.json")
contract, = root.glob("*/analysis/contract.json")
ident = read(contract)["task"]
assert report["task"] == ident
assert all(check_value(ident, "analysis", item, expected, read(root / "inputs/request.json")) for item in
           (report["result"], report["results"]["analysis"], read(root / "outputs/analysis.json")))
print("Public example passed")
