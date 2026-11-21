import json
import math
from pathlib import Path


def _check_finite(value):
    if isinstance(value, bool):
        raise ValueError("boolean is not a finite number")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite number")
        return value
    raise ValueError("not a number")


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        data = json.loads(text, parse_constant=lambda s: (_ for _ in ()).throw(ValueError("non-finite JSON")))
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("invalid JSON") from exc
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level must be object or array")
    return data
