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
    result = transform(payloads, contract)
    out = root / contract["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    contract_path = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "chain" / "contract.json"
    build_component(root, contract_path)
