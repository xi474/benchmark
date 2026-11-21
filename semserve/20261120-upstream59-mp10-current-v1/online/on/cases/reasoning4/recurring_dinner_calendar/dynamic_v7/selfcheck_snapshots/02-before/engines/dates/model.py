import json
import math
from pathlib import Path


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
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON") from exc
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level must be object or array")
    _reject_non_finite(data)
    return data
