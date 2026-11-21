import math


def _is_finite_number(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    payload = _unwrap(payloads[0])
    if not isinstance(payload, dict):
        raise ValueError("input must be an object")

    columns = payload.get("columns")
    pieces = payload.get("pieces")
    attribute_policy = payload.get("attribute_policy")

    if not isinstance(columns, list):
        raise ValueError("columns must be a list")
    if not isinstance(pieces, list):
        raise ValueError("pieces must be a list")
    if attribute_policy not in ("drop_conflicts", "first"):
        raise ValueError("invalid attribute_policy")

    # columns: unique non-empty strings
    seen_columns = set()
    for col in columns:
        if not isinstance(col, str) or not col.strip():
            raise ValueError("invalid column name")
        if col in seen_columns:
            raise ValueError("duplicate column")
        seen_columns.add(col)

    piece_ids = set()
    all_coords = set()
    order = []

    for piece in pieces:
        if not isinstance(piece, dict):
            raise ValueError("piece must be an object")
        pid = piece.get("id")
        coords = piece.get("coordinates")
        data = piece.get("data")
        attrs = piece.get("attrs")

        if not isinstance(pid, str) or not pid.strip():
            raise ValueError("invalid piece id")
        if pid in piece_ids:
            raise ValueError("duplicate piece id")
        piece_ids.add(pid)

        if not isinstance(coords, list):
            raise ValueError("coordinates must be a list")
        if not isinstance(data, list):
            raise ValueError("data must be a list")
        if not isinstance(attrs, dict):
            raise ValueError("attrs must be an object")

        if len(coords) != len(data):
            raise ValueError("coordinates/data length mismatch")

        for coord in coords:
            if not _is_finite_number(coord):
                raise ValueError("invalid coordinate")
            if coord in all_coords:
                raise ValueError("overlapping coordinate")
            all_coords.add(coord)

        for row_idx, row in enumerate(data):
            if not isinstance(row, list):
                raise ValueError("data row must be a list")
            if len(row) != len(columns):
                raise ValueError("data row width mismatch")
            for value in row:
                if not _is_finite_number(value):
                    raise ValueError("invalid data value")
            order.append({"coordinate": coords[row_idx], "piece": pid, "row": row_idx})

    order.sort(key=lambda entry: entry["coordinate"])

    return {"name": contract["name"], "result": {"columns": columns, "order": order}}
