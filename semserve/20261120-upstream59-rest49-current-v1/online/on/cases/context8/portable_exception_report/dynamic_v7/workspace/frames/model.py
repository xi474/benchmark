import json
from pathlib import Path


def load_payload(path):
    """Read a UTF-8 JSON file. Only object/array top-level is legal.

    Invalid JSON, other top-level types, and any nested NaN/Infinity raise
    ValueError.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError("cannot read payload: %s" % (exc,)) from exc
    try:
        data = json.loads(text, parse_constant=_reject_constant)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("invalid JSON: %s" % (exc,)) from exc
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level JSON must be an object or array")
    return data


def _reject_constant(value):
    raise ValueError("non-finite number is not allowed")
