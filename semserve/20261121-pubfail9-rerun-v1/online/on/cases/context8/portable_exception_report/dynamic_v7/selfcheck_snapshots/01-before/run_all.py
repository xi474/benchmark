import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    # Optional materialization step.
    materialize = ROOT / "materialize.py"
    if materialize.is_file():
        subprocess.run(
            [sys.executable, str(materialize)],
            cwd=ROOT,
            check=True,
        )

    # Run each component's render CLI in dependency order.
    components = ["chain", "frames", "report"]
    for name in components:
        render = ROOT / name / "render.py"
        contract = ROOT / name / "contract.json"
        subprocess.run(
            [sys.executable, str(render), str(ROOT), str(contract)],
            cwd=ROOT,
            check=True,
        )

    # Integrate component outputs into the core manifest.
    subprocess.run(
        [sys.executable, str(ROOT / "integrate.py")],
        cwd=ROOT,
        check=True,
    )

    # Produce the final report.
    subprocess.run(
        [sys.executable, str(ROOT / "final_report.py")],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
