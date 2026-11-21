import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    # Run each component's render CLI in dependency order.
    for comp in ("parts", "encoding", "body"):
        subprocess.run(
            [sys.executable, str(ROOT / comp / "render.py")],
            cwd=ROOT,
            check=True,
        )
    subprocess.run(
        [sys.executable, str(ROOT / "integrate.py")],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "final_report.py")],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
