import json
from pathlib import Path


def _reject_non_finite(value):
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non-finite number in JSON payload")
    elif isinstance(value, dict):
        for v in value.values():
            _reject_non_finite(v)
    elif isinstance(value, list):
        for v in value:
            _reject_non_finite(v)


def load_payload(path):
    text = Path(path).read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON payload") from exc
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level JSON must be object or array")
    _reject_non_finite(data)
    return data
