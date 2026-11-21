import json
import math
from pathlib import Path


def _check_finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite number")
    return value


def _reject_non_finite(obj):
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError("non-finite number")
    elif isinstance(obj, list):
        for item in obj:
            _reject_non_finite(item)
    elif isinstance(obj, dict):
        for value in obj.values():
            _reject_non_finite(value)


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        data = json.loads(text, parse_constant=lambda c: (_ for _ in ()).throw(ValueError("non-finite number")))
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("invalid JSON") from exc
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level must be object or array")
    _reject_non_finite(data)
    return data
