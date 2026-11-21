import json
from pathlib import Path


def _check_finite(value, path):
    if isinstance(value, bool):
        raise ValueError(f"invalid type at {path}")
    if isinstance(value, (int, float)):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError(f"non-finite number at {path}")
        return
    raise ValueError(f"invalid type at {path}")


def _reject_non_finite(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _reject_non_finite(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _reject_non_finite(v, f"{path}[{i}]")
    elif isinstance(obj, float):
        if obj != obj or obj in (float("inf"), float("-inf")):
            raise ValueError(f"non-finite number at {path}")


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON: {e}") from e
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level must be object or array")
    _reject_non_finite(data)
    return data
