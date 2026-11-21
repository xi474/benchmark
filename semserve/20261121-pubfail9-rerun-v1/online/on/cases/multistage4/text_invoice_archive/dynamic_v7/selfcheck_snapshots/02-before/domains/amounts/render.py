import json
import sys
from pathlib import Path

from model import load_payload
from transform import transform


def build_component(root: Path, contract_path: Path):
    contract = load_payload(contract_path)
    payloads = [load_payload(root / p) for p in contract["inputs"]]
    return transform(payloads, contract)


def main():
    root = Path.cwd()
    contract_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("contract.json")
    result = build_component(root, contract_path)
    contract = load_payload(contract_path)
    out_path = root / contract["output"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
