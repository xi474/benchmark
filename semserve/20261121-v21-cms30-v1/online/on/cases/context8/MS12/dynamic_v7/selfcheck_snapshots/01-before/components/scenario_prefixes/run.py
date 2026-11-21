from pathlib import Path
import runpy
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
sys.argv[1:1] = ["run", "scenario_prefixes"]
runpy.run_path(str(root / "component_runtime.py"), run_name="__main__")
