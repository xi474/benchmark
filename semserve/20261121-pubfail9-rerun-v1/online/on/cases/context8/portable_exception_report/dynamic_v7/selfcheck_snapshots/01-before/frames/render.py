import json
import sys
from pathlib import Path

try:
    from .model import load_payload
    from .transform import transform
except ImportError:
    from model import load_payload
    from transform import transform


def build_component(root, contract_path):
    root = Path(root)
    contract = load_payload(contract_path)
    payloads = [load_payload(root / p) for p in contract["inputs"]]
    result = transform(payloads, contract)
    out = root / contract["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2,
                   allow_nan=False) + "\n",
        encoding="utf-8")
    return result


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: render.py <root> <contract_path>")
    build_component(sys.argv[1], sys.argv[2])
