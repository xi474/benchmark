"""Shared model helpers: strict JSON payload loading."""

import json
import math
from pathlib import Path


def _reject_non_finite(value):
    """Raise ValueError if value contains NaN or Infinity anywhere."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite number is not allowed")
    elif isinstance(value, dict):
        for v in value.values():
            _reject_non_finite(v)
    elif isinstance(value, list):
        for v in value:
            _reject_non_finite(v)


def load_payload(path: Path):
    """Read a UTF-8 JSON file; only object/array top level is legal.

    Raises ValueError for invalid JSON, non-object/array top level, and any
    nested NaN/Infinity.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text, parse_constant=_reject_constant)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("invalid JSON: %s" % exc) from exc

    if not isinstance(data, (dict, list)):
        raise ValueError("top-level JSON must be an object or array")

    _reject_non_finite(data)
    return data


def _reject_constant(value):
    raise ValueError("non-finite number is not allowed: %s" % value)
