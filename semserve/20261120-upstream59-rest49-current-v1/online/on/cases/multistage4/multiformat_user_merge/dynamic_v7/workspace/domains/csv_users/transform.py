import csv
import io
import math


def transform(payloads, contract):
    """Merge CSV user rows into a directory of records.

    payloads must match contract["inputs"] order and count. Returns
    {"name": contract["name"], "result": {"records": [...]}}.
    """
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count does not match contract inputs")

    payload = payloads[0]
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    csv_text = payload.get("csv_text")
    if csv_text is None:
        raise ValueError("missing csv_text")

    rows = _parse_csv(csv_text)
    records = _merge_rows(rows)

    return {"name": contract["name"], "result": {"records": records}}


def _parse_csv(csv_text):
    if not isinstance(csv_text, str):
        raise ValueError("csv_text must be a string")
    if csv_text == "":
        return []

    reader = csv.reader(io.StringIO(csv_text))
    try:
        header = next(reader)
    except StopIteration:
        return []

    if "id" in header and "user_id" in header:
        raise ValueError("both id and user_id columns present")
    if "id" not in header and "user_id" not in header:
        raise ValueError("missing id or user_id column")

    if len(set(header)) != len(header):
        raise ValueError("duplicate column names")

    rows = []
    for line in reader:
        if len(line) != len(header):
            raise ValueError("row has wrong number of columns")
        row = dict(zip(header, line))
        rows.append(row)
    return rows


def _merge_rows(rows):
    merged = {}
    order = []
    for row in rows:
        id_value = _resolve_id(row)
        if id_value is None:
            continue
        key = id_value
        if key not in merged:
            merged[key] = {}
            order.append(key)
        rec = merged[key]
        for field in ("name", "full_name", "email", "mail", "joined", "joined_at"):
            if field in row:
                value = row[field]
                if value != "":
                    rec[field] = value

    records = []
    for key in sorted(order, key=lambda k: str(k)):
        rec = merged[key]
        out = {"id": str(key)}
        name = _pick(rec, "name", "full_name")
        if name is not None:
            out["name"] = name
        email = _pick(rec, "email", "mail")
        if email is not None:
            out["email"] = email
        joined = _pick(rec, "joined", "joined_at")
        if joined is not None:
            out["joined"] = _normalize_date(joined)
        records.append(out)
    return records


def _resolve_id(row):
    if "id" in row:
        raw = row["id"]
    else:
        raw = row["user_id"]
    if raw == "":
        return None
    if isinstance(raw, bool):
        raise ValueError("id must not be bool")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if s == "":
            raise ValueError("id must be non-empty after strip")
        return s
    raise ValueError("id must be str or int")


def _pick(rec, *fields):
    for f in fields:
        if f in rec:
            return rec[f]
    return None


def _normalize_date(value):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError("joined must be a string")
    s = value.strip()
    if s == "":
        raise ValueError("joined must be non-empty after strip")
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        # YYYY-MM-DD
        y, m, d = s.split("-")
        if _valid_date(y, m, d):
            return s
        raise ValueError("invalid date")
    if len(s) == 10 and s[2] == "/" and s[5] == "/":
        # DD/MM/YYYY
        d, m, y = s.split("/")
        if _valid_date(y, m, d):
            return "%s-%s-%s" % (y, m, d)
        raise ValueError("invalid date")
    raise ValueError("joined must be YYYY-MM-DD or DD/MM/YYYY")


def _valid_date(y, m, d):
    if not (y.isdigit() and m.isdigit() and d.isdigit()):
        return False
    yi, mi, di = int(y), int(m), int(d)
    if not (1 <= mi <= 12):
        return False
    if not (1 <= di <= 31):
        return False
    import calendar
    return di <= calendar.monthrange(yi, mi)[1]
