import json
import math
from pathlib import Path


def _check_finite(value):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError("non-finite number")
    return value


def _validate(value):
    if isinstance(value, dict):
        return {k: _validate(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_validate(v) for v in value]
    if isinstance(value, float):
        return _check_finite(value)
    return value


def load_payload(path):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text, parse_constant=lambda s: (_ for _ in ()).throw(ValueError("non-finite number")))
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("invalid JSON") from exc
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level must be object or array")
    return _validate(data)
