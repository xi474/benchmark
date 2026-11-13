"""Generic JSON delivery helpers. Business logic belongs to the submission."""
import json
from pathlib import Path

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")

def build(root, contract, transform):
    root = Path(root)
    request = read(root / contract["bindings"]["request"])
    result = transform({"request": request}, contract)
    save(root / contract["output"], result)
    return result
