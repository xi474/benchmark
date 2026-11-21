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


def _write_json(path, data):
    text = json.dumps(
        data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
    ) + "\n"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    cp = here / "contract.json"
    result = build_component(root, cp)
    contract = load_payload(cp)
    _write_json(root / contract["output"], result)
