import json
from pathlib import Path


def _reject_nonfinite(value):
    if isinstance(value, float) and (value != value or value in (float('inf'), float('-inf'))):
        raise ValueError('non-finite number')
    if isinstance(value, dict):
        for v in value.values():
            _reject_nonfinite(v)
    elif isinstance(value, list):
        for v in value:
            _reject_nonfinite(v)


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    try:
        data = json.loads(text)
    except ValueError as e:
        raise ValueError('invalid JSON') from e
    if not isinstance(data, (dict, list)):
        raise ValueError('top-level must be object or array')
    _reject_nonfinite(data)
    return data
