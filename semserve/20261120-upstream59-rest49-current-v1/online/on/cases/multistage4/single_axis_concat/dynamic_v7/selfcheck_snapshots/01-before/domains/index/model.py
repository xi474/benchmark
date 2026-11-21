import json
import math
from pathlib import Path


def _check_finite(value):
    if isinstance(value, bool):
        raise ValueError("bool is not a finite number")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("non-finite number")
        return value
    raise ValueError("not a finite number")


def _reject_nonfinite(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("non-finite JSON value")
    elif isinstance(obj, list):
        for item in obj:
            _reject_nonfinite(item)
    elif isinstance(obj, dict):
        for value in obj.values():
            _reject_nonfinite(value)


def load_payload(path):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError("invalid JSON") from exc
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level must be object or array")
    _reject_nonfinite(data)
    return data
