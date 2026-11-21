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


def _write(path, data):
    text = json.dumps(
        data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
    )
    Path(path).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    root = here.parent
    contract_path = here / "contract.json"
    contract = load_payload(contract_path)
    result = build_component(root, contract_path)
    _write(root / contract["output"], result)
