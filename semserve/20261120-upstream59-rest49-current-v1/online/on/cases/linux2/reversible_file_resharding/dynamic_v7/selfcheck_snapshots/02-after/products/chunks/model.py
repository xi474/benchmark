import json
import math
from pathlib import Path


def _check_finite(value):
    if isinstance(value, bool):
        raise ValueError('bool is not a finite number')
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('non-finite number')
        return
    raise ValueError('not a number')


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    try:
        obj = json.loads(text, parse_constant=lambda s: (_ for _ in ()).throw(ValueError('non-finite JSON')))
    except ValueError:
        raise
    except Exception as e:
        raise ValueError('invalid JSON') from e
    if not isinstance(obj, (dict, list)):
        raise ValueError('top-level must be object or array')
    _reject_nonfinite(obj)
    return obj


def _reject_nonfinite(obj):
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError('non-finite number')
    elif isinstance(obj, dict):
        for v in obj.values():
            _reject_nonfinite(v)
    elif isinstance(obj, list):
        for v in obj:
            _reject_nonfinite(v)
