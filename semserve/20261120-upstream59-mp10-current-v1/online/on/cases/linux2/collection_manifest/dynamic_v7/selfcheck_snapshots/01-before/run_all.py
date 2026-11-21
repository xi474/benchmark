import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    # Run each component render.py in dependency order.
    components = ["inventory", "selection", "archive"]
    for name in components:
        script = ROOT / "products" / name / "render.py"
        subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)
    # Integrate all component outputs.
    subprocess.run([sys.executable, str(ROOT / "integrate.py")], cwd=ROOT, check=True)
    # Produce the final report.
    subprocess.run([sys.executable, str(ROOT / "final_report.py")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
