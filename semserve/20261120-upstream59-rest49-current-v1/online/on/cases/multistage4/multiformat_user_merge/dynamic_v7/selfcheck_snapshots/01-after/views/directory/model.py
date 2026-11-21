import json
from pathlib import Path


def _reject_nonfinite(obj):
    if isinstance(obj, float):
        if obj != obj or obj in (float('inf'), float('-inf')):
            raise ValueError('non-finite number')
    elif isinstance(obj, dict):
        for v in obj.values():
            _reject_nonfinite(v)
    elif isinstance(obj, list):
        for v in obj:
            _reject_nonfinite(v)


def load_payload(path):
    text = Path(path).read_text(encoding='utf-8')
    data = json.loads(text, parse_constant=lambda s: (_ for _ in ()).throw(ValueError('non-finite number')))
    if not isinstance(data, (dict, list)):
        raise ValueError('top-level must be object or array')
    _reject_nonfinite(data)
    return data
