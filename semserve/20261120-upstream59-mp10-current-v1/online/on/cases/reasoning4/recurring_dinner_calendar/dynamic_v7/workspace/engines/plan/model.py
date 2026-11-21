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
    elif isinstance(obj, dict):
        for v in obj.values():
            _reject_non_finite(v)
    elif isinstance(obj, list):
        for v in obj:
            _reject_non_finite(v)


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        data = json.loads(text, parse_constant=lambda s: (_ for _ in ()).throw(ValueError("non-finite number")))
    except ValueError:
        raise
    except Exception as e:
        raise ValueError("invalid JSON") from e
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level must be object or array")
    _reject_non_finite(data)
    return data
