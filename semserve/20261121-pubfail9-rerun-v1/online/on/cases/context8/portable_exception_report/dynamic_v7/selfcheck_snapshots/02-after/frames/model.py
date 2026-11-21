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
        raise ValueError("top-level must be object or array")
    _check_finite(data)
    return data


def _reject_constant(value):
    raise ValueError("non-finite number not allowed")


def _check_finite(value):
    if isinstance(value, float):
        import math
        if not math.isfinite(value):
            raise ValueError("non-finite number not allowed")
    elif isinstance(value, dict):
        for v in value.values():
            _check_finite(v)
    elif isinstance(value, list):
        for v in value:
            _check_finite(v)
