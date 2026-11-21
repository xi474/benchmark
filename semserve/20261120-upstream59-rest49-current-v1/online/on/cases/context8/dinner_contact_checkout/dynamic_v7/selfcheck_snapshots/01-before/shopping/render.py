import json
import sys
from pathlib import Path

try:
    from .model import load_payload
    from .transform import transform
except ImportError:
    from model import load_payload
    from transform import transform


def build_component(root, contract_path):
    root = Path(root)
    contract_path = Path(contract_path)
    contract = load_payload(contract_path)
    payloads = [load_payload(root / p) for p in contract["inputs"]]
    return transform(payloads, contract)


def _write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    root = Path.cwd()
    contract_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("contract.json")
    contract = load_payload(contract_path)
    result = build_component(root, contract_path)
    _write_json(root / contract["output"], result)
