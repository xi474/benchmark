import json
import sys
from pathlib import Path

try:
    from .model import load_payload
    from .transform import transform
except ImportError:
    from model import load_payload
    from transform import transform


def _write_json(path, data):
    text = json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    )
    path.write_text(text + "\n", encoding="utf-8")


def build_component(root, contract_path):
    root = Path(root)
    contract_path = Path(contract_path)
    contract = load_payload(contract_path)
    payloads = [load_payload(root / p) for p in contract["inputs"]]
    result = transform(payloads, contract)
    out_path = root / contract["output"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out_path, result)
    return result


if __name__ == "__main__":
    contract_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("contract.json")
    root = Path.cwd()
    build_component(root, contract_path)
