import json
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
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    cp = here / "contract.json"
    contract = load_payload(cp)
    result = build_component(root, cp)
    _write_json(root / contract["output"], result)
