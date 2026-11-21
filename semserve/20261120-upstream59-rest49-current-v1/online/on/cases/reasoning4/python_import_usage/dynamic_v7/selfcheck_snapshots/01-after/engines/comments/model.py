import json
import math
from pathlib import Path


def _check_finite(value):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError("non-finite number")
    if isinstance(value, list):
        for v in value:
            _check_finite(v)
    elif isinstance(value, dict):
        for v in value.values():
            _check_finite(v)


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
    _check_finite(data)
    return data
