import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    # Recompute every component output in dependency order.
    components = [
        'products/chunks',
        'products/layout',
        'products/restore',
    ]
    for comp in components:
        render = ROOT / comp / 'render.py'
        subprocess.run([sys.executable, str(render)], cwd=ROOT, check=True)

    # Integrate all component outputs into the core manifest.
    subprocess.run([sys.executable, str(ROOT / 'integrate.py')], cwd=ROOT, check=True)

    # Produce the final report.
    subprocess.run([sys.executable, str(ROOT / 'final_report.py')], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
