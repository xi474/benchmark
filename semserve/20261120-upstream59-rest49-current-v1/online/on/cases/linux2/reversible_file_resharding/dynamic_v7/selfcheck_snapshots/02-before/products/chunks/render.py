import json
import sys
from pathlib import Path

from model import load_payload
from transform import transform


def build_component(root, contract_path):
    root = Path(root)
    cp = Path(contract_path)
    contract = load_payload(cp)
    payloads = [load_payload(root / p) for p in contract['inputs']]
    return transform(payloads, contract)


def _write_json(path, obj):
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'
    Path(path).write_text(text, encoding='utf-8')


def main():
    root = Path(__file__).resolve().parents[2]
    cp = Path(__file__).with_name('contract.json')
    result = build_component(root, cp)
    contract = load_payload(cp)
    out = root / contract['output']
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out, result)


if __name__ == '__main__':
    main()
