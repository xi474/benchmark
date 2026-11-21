import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from model import load_payload
from transform import transform


def build_component(root, contract_path):
    contract = load_payload(contract_path)
    payloads = [load_payload(root / p) for p in contract['inputs']]
    return transform(payloads, contract)


def main():
    cp = Path(__file__).with_name('contract.json')
    contract = load_payload(cp)
    result = build_component(ROOT, cp)
    out = ROOT / contract['output']
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2,
                   allow_nan=False) + '\n',
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()
