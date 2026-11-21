"""Implement the business transform. I/O helpers are supplied and editable here."""
from pathlib import Path
import json
from runtime import build

def transform(payload, contract):
    orders = payload["orders"]
    result = []
    for rec in orders:
        result.append({
            "buyer": rec[0:4],
            "seller": rec[4:8],
            "book": rec[8:12],
            "amount": int(rec[12:22]),
        })
    return result

def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def build_component(root, contract):
    return build(root, contract, transform)
