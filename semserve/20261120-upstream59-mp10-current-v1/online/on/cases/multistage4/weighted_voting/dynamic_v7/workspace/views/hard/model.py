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


def _validate_no_nonfinite(obj):
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError('non-finite JSON value')
    elif isinstance(obj, dict):
        for v in obj.values():
            _validate_no_nonfinite(v)
    elif isinstance(obj, list):
        for v in obj:
            _validate_no_nonfinite(v)


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError('invalid JSON') from e
    if not isinstance(data, (dict, list)):
        raise ValueError('top-level must be object or array')
    _validate_no_nonfinite(data)
    return data
