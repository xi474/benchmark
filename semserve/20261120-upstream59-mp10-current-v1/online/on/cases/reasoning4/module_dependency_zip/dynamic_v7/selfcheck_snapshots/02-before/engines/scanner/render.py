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
    result = transform(payloads, contract)
    out = root / contract["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result


def main():
    here = Path(__file__).resolve()
    component_dir = here.parent
    root = here.parents[2]
    cp = component_dir / "contract.json"
    build_component(root, cp)


if __name__ == "__main__":
    main()
