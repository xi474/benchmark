import json
from pathlib import Path


def load_payload(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        data = json.loads(text, parse_constant=lambda c: (_raise(c)))
    except ValueError:
        raise
    if not isinstance(data, (dict, list)):
        raise ValueError("top-level must be object or array")
    return data


def _raise(c):
    raise ValueError("non-standard JSON number: %s" % c)
