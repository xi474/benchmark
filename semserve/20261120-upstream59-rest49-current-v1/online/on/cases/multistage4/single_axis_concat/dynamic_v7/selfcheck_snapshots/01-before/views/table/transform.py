def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    original = _unwrap(payloads[0])
    index = _unwrap(payloads[1])
    attributes = _unwrap(payloads[2])

    if not isinstance(original, dict):
        raise ValueError("original input must be an object")
    if not isinstance(index, dict):
        raise ValueError("index result must be an object")
    if not isinstance(attributes, dict):
        raise ValueError("attributes result must be an object")

    columns = original.get("columns")
    pieces = original.get("pieces")
    if not isinstance(columns, list):
        raise ValueError("columns must be a list")
    if not isinstance(pieces, list):
        raise ValueError("pieces must be a list")

    order = index.get("order")
    if not isinstance(order, list):
        raise ValueError("order must be a list")

    attrs = attributes.get("attrs")
    conflicts = attributes.get("conflicts")
    if not isinstance(attrs, dict):
        raise ValueError("attrs must be an object")
    if not isinstance(conflicts, list):
        raise ValueError("conflicts must be a list")

    # Build lookup from piece id -> piece
    piece_map = {}
    for piece in pieces:
        if not isinstance(piece, dict):
            raise ValueError("piece must be an object")
        pid = piece.get("id")
        if pid not in piece_map:
            piece_map[pid] = piece

    coordinates = []
    data = []
    for entry in order:
        if not isinstance(entry, dict):
            raise ValueError("order entry must be an object")
        coord = entry.get("coordinate")
        pid = entry.get("piece")
        row = entry.get("row")
        if pid not in piece_map:
            raise ValueError("unknown piece id in order")
        piece = piece_map[pid]
        piece_data = piece.get("data")
        if not isinstance(piece_data, list) or not (0 <= row < len(piece_data)):
            raise ValueError("invalid row index in order")
        coordinates.append(coord)
        data.append(piece_data[row])

    return {
        "name": contract["name"],
        "result": {
            "coordinates": coordinates,
            "columns": columns,
            "data": data,
            "attrs": attrs,
            "attribute_conflicts": conflicts,
        },
    }
