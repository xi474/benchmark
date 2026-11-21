"""Shared model loading for feature configuration components.

Only the standard library is used.  ``load_payload`` reads a UTF-8 JSON file
and enforces the strict top-level and numeric rules required by the task
specification.
"""

import json
import math
from pathlib import Path


def _reject_non_finite(value):
    """Raise ValueError if ``value`` contains a non-finite number anywhere."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite number is not allowed")
    elif isinstance(value, dict):
        for item in value.values():
            _reject_non_finite(item)
    elif isinstance(value, list):
        for item in value:
            _reject_non_finite(item)


def load_payload(path):
    """Read a UTF-8 JSON file and return the parsed value.

    Only a JSON object or array is a legal top-level value.  Invalid JSON,
    any other top-level type, and any nested NaN/Infinity raise ValueError.
    """
    if not isinstance(path, Path):
        path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError("cannot read payload file: %s" % (exc,)) from exc
    try:
        value = json.loads(text)
    except ValueError as exc:
        raise ValueError("invalid JSON payload: %s" % (exc,)) from exc
    if not isinstance(value, (dict, list)):
        raise ValueError("top-level JSON value must be an object or array")
    _reject_non_finite(value)
    return value
