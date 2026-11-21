def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    # Each payload is a component wrapper {"name": ..., "result": {...}}.
    # The business input is the "result" object.
    branches = []
    for payload in payloads:
        if isinstance(payload, dict) and set(payload) == {"name", "result"}:
            payload = payload["result"]
        branches.append(payload)

    numeric, category, time_ = branches

    # Collect per-branch key -> values mapping.
    def rows_to_map(rows):
        return {row["key"]: row["values"] for row in rows}

    num_map = rows_to_map(numeric["rows"])
    cat_map = rows_to_map(category["rows"])
    time_map = rows_to_map(time_["rows"])

    # Column names with prefixes.
    num_cols = ["num." + c for c in sorted(num_map[next(iter(num_map))])] if num_map else []
    cat_cols = ["cat." + c for c in sorted(cat_map[next(iter(cat_map))])] if cat_map else []
    time_cols = ["time." + c for c in sorted(time_map[next(iter(time_map))])] if time_map else []

    # Determine column sets from the actual values present in each branch.
    # Use the union of keys across all rows in each branch to be safe.
    def branch_columns(branch_map, prefix):
        cols = set()
        for values in branch_map.values():
            for c in values:
                cols.add(prefix + c)
        return cols

    num_cols = branch_columns(num_map, "num.")
    cat_cols = branch_columns(cat_map, "cat.")
    time_cols = branch_columns(time_map, "time.")

    columns = sorted(num_cols | cat_cols | time_cols)

    # All keys (outer join).
    all_keys = sorted(set(num_map) | set(cat_map) | set(time_map))

    data = []
    for key in all_keys:
        row = []
        for col in columns:
            if col.startswith("num."):
                values = num_map.get(key)
                row.append(values.get(col[len("num."):]) if values else None)
            elif col.startswith("cat."):
                values = cat_map.get(key)
                row.append(values.get(col[len("cat."):]) if values else None)
            else:  # time.
                values = time_map.get(key)
                row.append(values.get(col[len("time."):]) if values else None)
        data.append(row)

    return {
        "name": contract["name"],
        "result": {"index": all_keys, "columns": columns, "data": data},
    }
