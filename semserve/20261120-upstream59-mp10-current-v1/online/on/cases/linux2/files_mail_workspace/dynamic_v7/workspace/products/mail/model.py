import json
from pathlib import Path


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        data = json.loads(text, parse_constant=_reject_constant)
    except ValueError:
        raise
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level JSON must be an object or array")
    return data


def _reject_constant(value):
    raise ValueError("non-finite number not allowed")
