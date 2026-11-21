import json
import sys
from pathlib import Path

from model import load_payload
from transform import transform


def build_component(root, contract_path):
    root = Path(root)
    contract_path = Path(contract_path)
    contract = load_payload(contract_path)
    payloads = [load_payload(root / p) for p in contract['inputs']]
    return transform(payloads, contract)


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'
    path.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    contract_path = here / 'contract.json'
    result = build_component(root, contract_path)
    contract = load_payload(contract_path)
    _write_json(root / contract['output'], result)
