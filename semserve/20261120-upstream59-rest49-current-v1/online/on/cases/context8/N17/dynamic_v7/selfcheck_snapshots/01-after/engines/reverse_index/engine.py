"""Implement the business transform. I/O helpers are supplied and editable here."""
from pathlib import Path
import json
from runtime import build


def transform(payload, contract):
    dependencies = payload["dependencies"]
    index = {}
    for template_id, keys in dependencies.items():
        for key in keys:
            index.setdefault(key, []).append(template_id)
    for key in index:
        index[key] = sorted(set(index[key]))
    return index


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(root, contract):
    return build(root, contract, transform)
