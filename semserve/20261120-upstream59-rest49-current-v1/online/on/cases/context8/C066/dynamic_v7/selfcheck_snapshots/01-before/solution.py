from pathlib import Path
import json


def transform(payload):
    initial = payload["initial"]
    txs = payload["txs"]

    # rows: key -> {"body": ..., "rank": ...}
    rows = {k: dict(v) for k, v in initial.items()}

    committed = set()
    log = []

    for tx in txs:
        lsn = tx["lsn"]
        if lsn in committed:
            log.append([lsn, "REPLAY"])
            continue

        statements = tx["statements"]
        # Work on a copy; commit only if all statements succeed.
        snapshot = {k: dict(v) for k, v in rows.items()}
        ok = True

        for stmt in statements:
            if not ok:
                break
            # Validate and collect operations.
            # old identities to remove (U/D), new rows to place (I/U).
            removals = []  # list of old keys
            placements = []  # list of (new_key, body, rank)

            # First pass: validate existence and type markers.
            for op in stmt:
                o = op["op"]
                if o in ("U", "D"):
                    old = op["old"]
                    if old not in snapshot:
                        ok = False
                        break
                if o == "I":
                    cols = op["cols"]
                    colmap = {}
                    for c in cols:
                        colmap[c["name"]] = c
                    if not ("key" in colmap and "body" in colmap and "rank" in colmap):
                        ok = False
                        break
                    # type markers
                    if colmap["key"]["type"] != "text":
                        ok = False
                        break
                    if colmap["body"]["type"] != "text":
                        ok = False
                        break
                    if colmap["rank"]["type"] != "int":
                        ok = False
                        break
                if o == "U":
                    cols = op["cols"]
                    for c in cols:
                        name = c["name"]
                        if name == "key" and c["type"] != "text":
                            ok = False
                            break
                        if name == "body" and c["type"] != "text":
                            ok = False
                            break
                        if name == "rank" and c["type"] != "int":
                            ok = False
                            break
                    if not ok:
                        break
            if not ok:
                break

            # Second pass: compute removals and placements.
            for op in stmt:
                o = op["op"]
                if o == "D":
                    removals.append(op["old"])
                elif o == "U":
                    old = op["old"]
                    removals.append(old)
                    cols = op["cols"]
                    colmap = {c["name"]: c for c in cols}
                    new_key = colmap["key"]["value"] if "key" in colmap else old
                    old_row = snapshot[old]
                    body = colmap["body"]["value"] if "body" in colmap else old_row["body"]
                    rank = colmap["rank"]["value"] if "rank" in colmap else old_row["rank"]
                    placements.append((new_key, body, rank))
                elif o == "I":
                    cols = op["cols"]
                    colmap = {c["name"]: c for c in cols}
                    new_key = colmap["key"]["value"]
                    body = colmap["body"]["value"]
                    rank = colmap["rank"]["value"]
                    placements.append((new_key, body, rank))

            # Validate new key collisions among placements.
            seen = set()
            for new_key, body, rank in placements:
                if new_key in seen:
                    ok = False
                    break
                seen.add(new_key)
            if not ok:
                break

            # Apply: remove old identities, then place new rows.
            for old in removals:
                del snapshot[old]
            for new_key, body, rank in placements:
                snapshot[new_key] = {"body": body, "rank": rank}

        if ok:
            rows = snapshot
            committed.add(lsn)
            log.append([lsn, "COMMIT"])
        else:
            log.append([lsn, "ABORT"])

    return {"log": log, "rows": rows}


def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value
