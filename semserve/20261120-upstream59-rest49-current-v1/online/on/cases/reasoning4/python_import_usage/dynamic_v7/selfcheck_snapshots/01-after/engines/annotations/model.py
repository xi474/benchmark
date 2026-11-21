import json
from pathlib import Path


def load_payload(path):
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        raise ValueError("cannot read payload: %s" % e)
    try:
        data = json.loads(text, parse_constant=_reject_constant)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError("invalid JSON: %s" % e)
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level must be object or array")
    return data


def _reject_constant(value):
    raise ValueError("non-finite number not allowed")
