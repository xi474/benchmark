"""Implement the business transform. I/O helpers are supplied and editable here."""
from pathlib import Path
import json
from runtime import build


def transform(payload, contract):
    text = payload["text"]
    records = []
    for i in range(0, len(text), 34):
        rec = text[i:i + 34]
        records.append({
            "id": rec[0:4],
            "name": rec[4:24].rstrip(" "),
            "balance": int(rec[24:34]),
        })
    return records


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(root, contract):
    return build(root, contract, transform)
