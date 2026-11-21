import json
import sys
from pathlib import Path

from model import load_payload
from transform import transform


def build_component(root, contract_path):
    """Read all inputs under root, run transform, and return the wrapper."""
    contract = load_payload(contract_path)
    payloads = [load_payload(root / p) for p in contract['inputs']]
    return transform(payloads, contract)


def _dump(obj):
    return json.dumps(
        obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
    ) + '\n'


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        contract_path = Path(args[0]).resolve()
    else:
        contract_path = Path(__file__).resolve().parent / 'contract.json'
    if not contract_path.is_file():
        raise FileNotFoundError('contract.json not found: %s' % contract_path)
    contract = load_payload(contract_path)
    root = contract_path.parents[2]
    result = build_component(root, contract_path)
    out = root / contract['output']
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_dump(result), encoding='utf-8')


if __name__ == '__main__':
    main()
