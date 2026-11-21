import json
import sys
from pathlib import Path

try:
    from .model import load_payload
    from .transform import transform
except ImportError:
    from model import load_payload
    from transform import transform


def _write_json(path, obj):
    text = json.dumps(
        obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
    ) + "\n"
    Path(path).write_text(text, encoding="utf-8")


def build_component(root, contract_path):
    root = Path(root)
    contract_path = Path(contract_path)
    contract = load_payload(contract_path)
    payloads = [load_payload(root / p) for p in contract["inputs"]]
    result = transform(payloads, contract)
    out_path = root / contract["output"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out_path, result)
    return result


if __name__ == "__main__":
    # Support any current directory: locate the workspace root as the parent
    # of the engines directory containing this file.
    here = Path(__file__).resolve()
    component_dir = here.parent
    root = here.parents[2]
    contract_path = component_dir / "contract.json"
    build_component(root, contract_path)
