import math


def _is_finite_number(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return True
    if isinstance(v, float):
        return math.isfinite(v)
    return False


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    data = _unwrap(payloads[0])
    if not isinstance(data, dict):
        raise ValueError("input must be object")

    criteria = data.get("criteria")
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be object")

    filters = criteria.get("filters")
    if not isinstance(filters, list):
        raise ValueError("filters must be list")

    limit = criteria.get("limit")
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be int")
    if limit < 1 or limit > 100:
        raise ValueError("limit out of range")

    allowed_fields = {"id", "name", "track_count", "duration"}
    allowed_ops = {"eq", "ne", "gt", "ge", "lt", "le"}

    clauses = []
    params = []
    for f in filters:
        if not isinstance(f, dict):
            raise ValueError("filter must be object")
        field = f.get("field")
        op = f.get("op")
        value = f.get("value")
        if field not in allowed_fields:
            raise ValueError("invalid field")
        if op not in allowed_ops:
            raise ValueError("invalid op")
        if field in ("id", "name"):
            if not isinstance(value, str):
                raise ValueError("id/name value must be str")
            if op not in ("eq", "ne"):
                raise ValueError("id/name only support eq/ne")
        else:
            if not _is_finite_number(value) or value < 0:
                raise ValueError("stat field value must be non-negative finite number")
        clauses.append(f"{field} {op.upper()} ?")
        params.append(value)

    sql = "SELECT id FROM playlists"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id LIMIT ?"
    params.append(limit)

    return {"name": contract["name"], "result": {"sql": sql, "params": params}}
