import json
import math
from pathlib import Path


def _check_finite(value):
    if isinstance(value, bool):
        raise ValueError("bool is not a valid number")
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("non-finite number")
        return
    raise ValueError("expected number")


def _validate(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            _validate(v)
    elif isinstance(obj, list):
        for v in obj:
            _validate(v)
    elif isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError("non-finite number")
    elif isinstance(obj, (str, int, bool)) or obj is None:
        pass
    else:
        raise ValueError("invalid JSON value")


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError("invalid JSON") from e
    if not isinstance(obj, (dict, list)):
        raise ValueError("top-level must be object or array")
    _validate(obj)
    return obj
