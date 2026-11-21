import json
import sys
from pathlib import Path

from model import load_payload
from transform import transform


def build_component(root, contract_path):
    root = Path(root)
    cp = Path(contract_path)
    contract = load_payload(cp)
    payloads = [load_payload(root / p) for p in contract["inputs"]]
    return transform(payloads, contract)


def _write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    contract_path = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "parts" / "contract.json"
    contract = load_payload(contract_path)
    result = build_component(root, contract_path)
    _write_json(root / contract["output"], result)
