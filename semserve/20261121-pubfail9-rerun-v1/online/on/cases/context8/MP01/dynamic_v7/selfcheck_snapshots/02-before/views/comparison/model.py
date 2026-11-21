import json
import math
from pathlib import Path


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        obj = json.loads(text, parse_constant=_reject_constant)
    except ValueError:
        raise
    if not isinstance(obj, (dict, list)):
        raise ValueError("top-level must be object or array")
    return obj


def _reject_constant(value):
    raise ValueError("non-finite number not allowed")
