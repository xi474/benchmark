import json
from pathlib import Path


def _check_finite(obj):
    if isinstance(obj, float):
        import math
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("non-finite number")
    elif isinstance(obj, dict):
        for v in obj.values():
            _check_finite(v)
    elif isinstance(obj, list):
        for v in obj:
            _check_finite(v)


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        data = json.loads(text, parse_constant=lambda c: (_ for _ in ()).throw(ValueError("non-finite number")))
    except ValueError:
        raise
    except Exception as e:
        raise ValueError("invalid JSON") from e
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level must be object or array")
    _check_finite(data)
    return data
