import json
import math
from pathlib import Path


def _reject_nonfinite(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("non-finite number")
        return
    if isinstance(obj, list):
        for item in obj:
            _reject_nonfinite(item)
        return
    if isinstance(obj, dict):
        for value in obj.values():
            _reject_nonfinite(value)
        return


def load_payload(path):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text, parse_constant=lambda s: (_ for _ in ()).throw(ValueError("non-standard JSON number")))
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("invalid JSON") from exc
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level must be object or array")
    _reject_nonfinite(data)
    return data
