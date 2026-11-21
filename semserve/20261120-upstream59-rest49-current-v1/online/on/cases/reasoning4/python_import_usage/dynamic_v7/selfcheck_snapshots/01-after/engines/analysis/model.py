import json
import math
from pathlib import Path


def _check_finite(value):
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("non-finite number")
    elif isinstance(value, list):
        for item in value:
            _check_finite(item)
    elif isinstance(value, dict):
        for item in value.values():
            _check_finite(item)


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        data = json.loads(
            text,
            parse_constant=lambda s: (_ for _ in ()).throw(ValueError("non-finite number")),
        )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("invalid JSON") from exc
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level must be object or array")
    _check_finite(data)
    return data
