import json
import sys
from pathlib import Path

from model import load_payload
from transform import transform


def build_component(root, contract_path):
    root = Path(root)
    cp = Path(contract_path)
    c = load_payload(cp)
    payloads = [load_payload(root / p) for p in c["inputs"]]
    return transform(payloads, c)


def _write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    p.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    cp = here / "contract.json"
    c = load_payload(cp)
    result = build_component(root, cp)
    _write_json(root / c["output"], result)
