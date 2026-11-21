import json
import math
from pathlib import Path


def _reject_nonfinite(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("non-finite number")
        return
    if isinstance(obj, dict):
        for v in obj.values():
            _reject_nonfinite(v)
    elif isinstance(obj, list):
        for v in obj:
            _reject_nonfinite(v)


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError("invalid JSON") from e
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level must be object or array")
    _reject_nonfinite(data)
    return data
