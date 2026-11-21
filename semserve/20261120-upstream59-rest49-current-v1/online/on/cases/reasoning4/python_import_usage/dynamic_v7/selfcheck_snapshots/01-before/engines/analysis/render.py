import json
import sys
from pathlib import Path

from model import load_payload
from transform import transform


def build_component(root, contract_path):
    root = Path(root)
    contract = load_payload(contract_path)
    payloads = [load_payload(root / p) for p in contract["inputs"]]
    return transform(payloads, contract)


def main():
    root = Path.cwd()
    contract_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "contract.json"
    contract = load_payload(contract_path)
    result = build_component(root, contract_path)
    out = root / contract["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
