import json
import sys
from pathlib import Path

from model import load_payload
from transform import transform


def _write_json(path, data):
    text = json.dumps(
        data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False,
    ) + "\n"
    Path(path).write_text(text, encoding="utf-8")


def build_component(root, contract_path):
    """Read all inputs from root, run transform, write output, return wrapper."""
    root = Path(root)
    contract_path = Path(contract_path)
    contract = load_payload(contract_path)
    payloads = [load_payload(root / p) for p in contract["inputs"]]
    result = transform(payloads, contract)
    out = root / contract["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out, result)
    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: render.py <contract_path>")
    contract_path = Path(sys.argv[1])
    root = contract_path.resolve().parent.parent
    build_component(root, contract_path)
