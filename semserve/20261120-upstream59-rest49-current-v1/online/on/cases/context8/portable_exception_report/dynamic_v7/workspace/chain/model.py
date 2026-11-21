import json
import math
from pathlib import Path


def _check_finite(value, where):
    if isinstance(value, bool):
        raise ValueError(f"{where}: bool is not a valid number")
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{where}: non-finite number")
        return
    raise ValueError(f"{where}: expected number")


def _reject_non_finite(obj, where):
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError(f"{where}: non-finite number")
    if isinstance(obj, dict):
        for k, v in obj.items():
            _reject_non_finite(v, f"{where}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _reject_non_finite(v, f"{where}[{i}]")


def load_payload(path):
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, (dict, list)):
        raise ValueError(f"{path}: top-level must be object or array")
    _reject_non_finite(data, str(path))
    return data
