"""Implement the business transform. I/O helpers are supplied and editable here."""
from pathlib import Path
import json
from runtime import build


def _block_value(block):
    """Return a dense rows x cols integer matrix for a block (null data = zeros)."""
    rows = block["rows"]
    cols = block["cols"]
    if block["data"] is None:
        return [[0] * cols for _ in range(rows)]
    return block["data"]


def _matmul(a, b):
    """Multiply two dense integer matrices."""
    rows = len(a)
    inner = len(b)
    cols = len(b[0]) if inner else 0
    out = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        ai = a[i]
        oi = out[i]
        for k in range(inner):
            aik = ai[k]
            if aik:
                bk = b[k]
                for j in range(cols):
                    oi[j] += aik * bk[j]
    return out


def _is_zero(mat):
    return all(v == 0 for row in mat for v in row)


def _block_multiply(a, b):
    """Multiply two blocks, returning a shaped block (data=null when all zero)."""
    rows = a["rows"]
    cols = b["cols"]
    av = _block_value(a)
    bv = _block_value(b)
    prod = _matmul(av, bv)
    if _is_zero(prod):
        return {"rows": rows, "cols": cols, "data": None}
    return {"rows": rows, "cols": cols, "data": prod}


def transform(payload, contract):
    matrix = payload["matrix"]
    n = len(matrix)
    result = []
    for i in range(n):
        row = []
        for j in range(n):
            acc = None
            for k in range(n):
                term = _block_multiply(matrix[i][k], matrix[k][j])
                if acc is None:
                    acc = term
                else:
                    av = _block_value(acc)
                    bv = _block_value(term)
                    summed = [[av[r][c] + bv[r][c] for c in range(len(av[0]))]
                              for r in range(len(av))]
                    if _is_zero(summed):
                        acc = {"rows": acc["rows"], "cols": acc["cols"], "data": None}
                    else:
                        acc = {"rows": acc["rows"], "cols": acc["cols"], "data": summed}
            row.append(acc)
        result.append(row)
    return result


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(root, contract):
    return build(root, contract, transform)
