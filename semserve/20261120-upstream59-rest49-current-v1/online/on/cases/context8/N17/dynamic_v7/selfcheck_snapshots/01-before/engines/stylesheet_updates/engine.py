"""Implement the business transform. I/O helpers are supplied and editable here."""
from pathlib import Path
import json
from runtime import build


def transform(payload, contract):
    dependencies = payload["dependencies"]
    changed = set(payload["changed"])
    affected = sorted(
        tid for tid, keys in dependencies.items() if changed.intersection(keys)
    )
    return {"dependencies": dependencies, "affected": affected}


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(root, contract):
    return build(root, contract, transform)
