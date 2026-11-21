import json
from pathlib import Path


def _reject_constant(value):
    raise ValueError("non-finite number is not allowed")


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        data = json.loads(text, parse_constant=_reject_constant)
    except ValueError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError("invalid JSON payload") from exc
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level JSON value must be an object or array")
    return data
