import json
import math
from pathlib import Path


def _check_finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite number")
    return value


def _validate(obj):
    if isinstance(obj, float):
        _check_finite(obj)
    elif isinstance(obj, list):
        for item in obj:
            _validate(item)
    elif isinstance(obj, dict):
        for v in obj.values():
            _validate(v)


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        data = json.loads(text, parse_constant=lambda s: (_ for _ in ()).throw(ValueError("non-finite number")))
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("invalid JSON") from exc
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level must be object or array")
    _validate(data)
    return data
