"""Implement the business transform. I/O helpers are supplied and editable here."""
from pathlib import Path
import json
from runtime import build


def transform(payload, contract):
    matrix = payload["matrix"]
    row_sizes = [row[0]["rows"] for row in matrix]
    col_sizes = [matrix[0][j]["cols"] for j in range(len(matrix[0]))]
    return {"row_sizes": row_sizes, "col_sizes": col_sizes}


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(root, contract):
    return build(root, contract, transform)
