import json
import math
from pathlib import Path


def _reject_nonfinite(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("non-finite number")
        return obj
    if isinstance(obj, dict):
        return {k: _reject_nonfinite(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_reject_nonfinite(v) for v in obj]
    return obj


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
    _reject_nonfinite(data)
    return data
