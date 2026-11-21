import csv
import io
import math


def _check_finite(value):
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("non-finite number")
    elif isinstance(value, dict):
        for v in value.values():
            _check_finite(v)
    elif isinstance(value, list):
        for v in value:
            _check_finite(v)


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def _safe_segment(s):
    if not isinstance(s, str):
        raise ValueError("id must be string")
    if s == "" or s != s.strip():
        raise ValueError("id must be non-empty and stripped")
    if "/" in s or "\\" in s or ":" in s or s in (".", ".."):
        raise ValueError("id must be a safe single path segment")
    return s


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    documents = _unwrap(payloads[0])
    classification = _unwrap(payloads[1])
    amounts = _unwrap(payloads[2])

    if not isinstance(documents, dict) or "documents" not in documents:
        raise ValueError("missing documents")
    if not isinstance(classification, dict) or "classes" not in classification:
        raise ValueError("missing classes")
    if not isinstance(amounts, dict) or "amounts" not in amounts:
        raise ValueError("missing amounts")
    _check_finite(documents)
    _check_finite(classification)
    _check_finite(amounts)

    docs = documents["documents"]
    classes = classification["classes"]
    amts = amounts["amounts"]

    archives = []
    rows = []
    totals = {"invoice": "0.00", "receipt": "0.00"}

    def add_total(kind, total):
        if total is None:
            return
        cur = totals[kind]

        def cents(s):
            a, b = s.split(".")
            return int(a) * 100 + int(b)
        c = cents(cur) + cents(total)
        totals[kind] = "%d.%02d" % (c // 100, c % 100)

    for doc in docs:
        if not isinstance(doc, dict):
            raise ValueError("document must be object")
        _check_finite(doc)
        did = doc["id"]
        filename = doc["filename"]
        text = doc["text"]
        kind = classes[did]
        total = amts[did]["total"]
        vat = amts[did]["vat"]

        if kind in ("invoice", "receipt") and total is None:
            raise ValueError("invoice/receipt must have total")

        seg = _safe_segment(did)
        path = "classified/" + kind + "/" + seg + "/" + filename
        hexval = text.encode("utf-8").hex()
        archives.append({"path": path, "hex": hexval})
        rows.append({"id": did, "filename": filename, "kind": kind,
                     "total": total, "vat": vat})
        add_total(kind, total)

    archives.sort(key=lambda a: a["path"])
    rows.sort(key=lambda r: r["id"])

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["id", "filename", "kind", "total", "vat"])
    for r in rows:
        w.writerow([r["id"], r["filename"], r["kind"],
                    r["total"] if r["total"] is not None else "",
                    r["vat"]])
    csv_str = buf.getvalue()

    result = {
        "archives": archives,
        "rows": rows,
        "csv": csv_str,
        "totals": totals,
    }
    return {"name": contract["name"], "result": result}
