import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    contracts = sorted(ROOT.rglob("contract.json"))
    contracts = [c for c in contracts if "outputs" not in c.relative_to(ROOT).parts]
    if not contracts:
        raise SystemExit("no contracts found")

    # Topological order: files, mail, reply before commit (commit depends on their outputs).
    order = []
    names = {c.parent.name for c in contracts}
    for name in ("files", "mail", "reply", "commit"):
        if name in names:
            order.append(name)
    for c in contracts:
        if c.parent.name not in order:
            order.append(c.parent.name)

    for name in order:
        render = ROOT / "products" / name / "render.py"
        if not render.is_file():
            raise SystemExit(f"missing render.py for {name}")
        subprocess.run([sys.executable, str(render)], cwd=ROOT, check=True)

    subprocess.run([sys.executable, str(ROOT / "integrate.py")], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(ROOT / "final_report.py")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
