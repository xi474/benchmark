"""Implement the business transform. I/O helpers are supplied and editable here."""
from pathlib import Path
import json
from runtime import build


def _block_value(block):
    """Return a dense integer matrix for a block, treating null data as zeros."""
    data = block["data"]
    rows = block["rows"]
    cols = block["cols"]
    if data is None:
        return [[0] * cols for _ in range(rows)]
    return data


def _multiply_blocks(a, b):
    """Multiply two dense block matrices (lists of block rows)."""
    n = len(a)
    result = []
    for i in range(n):
        row = []
        for j in range(n):
            rows = a[i][0]["rows"]
            cols = b[0][j]["cols"]
            acc = [[0] * cols for _ in range(rows)]
            for k in range(n):
                left = _block_value(a[i][k])
                right = _block_value(b[k][j])
                for r in range(rows):
                    for c in range(cols):
                        acc[r][c] += sum(left[r][t] * right[t][c] for t in range(len(right)))
            if all(v == 0 for line in acc for v in line):
                data = None
            else:
                data = acc
            row.append({"rows": rows, "cols": cols, "data": data})
        result.append(row)
    return result


def transform(payload, contract):
    squared = payload["squared"]
    matrix = payload["matrix"]
    layout = payload["layout"]
    blocks = _multiply_blocks(squared, matrix)
    return {"layout": layout, "blocks": blocks}


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(root, contract):
    return build(root, contract, transform)
