import json
from pathlib import Path

from model import load_payload
from transform import transform


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
    ) + "\n"
    path.write_text(text, encoding="utf-8")


def build_component(root, contract_path):
    root = Path(root)
    contract_path = Path(contract_path)
    contract = load_payload(contract_path)
    payloads = [load_payload(root / p) for p in contract["inputs"]]
    result = transform(payloads, contract)
    _write_json(root / contract["output"], result)
    return result


if __name__ == "__main__":
    root = Path.cwd()
    contract_path = Path(__file__).with_name("contract.json")
    build_component(root, contract_path)
