import math


def _reject_non_finite(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("non-finite number")
    elif isinstance(obj, list):
        for item in obj:
            _reject_non_finite(item)
    elif isinstance(obj, dict):
        for value in obj.values():
            _reject_non_finite(value)


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    branches = []
    for payload in payloads:
        if isinstance(payload, dict) and set(payload) == {"name", "result"}:
            payload = payload["result"]
        if not isinstance(payload, dict):
            raise ValueError("payload must be object")
        _reject_non_finite(payload)
        branches.append(payload)

    if len(branches) != 3:
        raise ValueError("expected three branches")

    numeric, category, time_ = branches

    def rows_to_map(rows):
        return {row["key"]: row["values"] for row in rows}

    num_map = rows_to_map(numeric["rows"])
    cat_map = rows_to_map(category["rows"])
    time_map = rows_to_map(time_["rows"])

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
            else:
                values = time_map.get(key)
                row.append(values.get(col[len("time."):]) if values else None)
        data.append(row)

    return {
        "name": contract["name"],
        "result": {"index": all_keys, "columns": columns, "data": data},
    }
