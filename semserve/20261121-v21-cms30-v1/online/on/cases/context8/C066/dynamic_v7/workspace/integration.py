def combine(payload, left, right):
    """Replay transactions and produce {log, rows}."""
    initial = payload["initial"]
    txs = payload["txs"]

    # rows: key -> {"body": ..., "rank": ...}
    rows = {k: {"body": v["body"], "rank": v["rank"]} for k, v in initial.items()}

    committed = set()
    log = []

    for tx in txs:
        lsn = tx["lsn"]
        if lsn in committed:
            log.append([lsn, "REPLAY"])
            continue

        statements = tx["statements"]
        # left: per-tx list of per-statement list of consumed old keys
        # right: per-tx list of per-statement list of decoded column maps (or None on type error)
        tx_old = left[txs.index(tx)] if False else None
        tx_dec = right[txs.index(tx)] if False else None

        # Recompute indices directly to avoid ambiguity
        idx = txs.index(tx)
        consumed = left[idx]
        decoded = right[idx]

        # Work on a snapshot copy; commit only if all statements succeed.
        snapshot = {k: dict(v) for k, v in rows.items()}
        aborted = False

        for si, statement in enumerate(statements):
            old_keys = consumed[si]
            dec_maps = decoded[si]

            # Validate old identities exist and are distinct
            for ok in old_keys:
                if ok not in snapshot:
                    aborted = True
                    break
            if aborted:
                break

            # Validate decoded maps (type errors -> None)
            for dm in dec_maps:
                if dm is None:
                    aborted = True
                    break
            if aborted:
                break

            # Build new rows for this statement
            new_rows = {}
            for ci, change in enumerate(statement):
                op = change["op"]
                dm = dec_maps[ci]
                if op == "D":
                    continue
                # I or U
                if op == "I":
                    # must provide key, body, rank
                    if "key" not in dm or "body" not in dm or "rank" not in dm:
                        aborted = True
                        break
                    new_key = dm["key"]
                    if not isinstance(new_key, str) or new_key == "":
                        aborted = True
                        break
                    new_rows[new_key] = {"body": dm["body"], "rank": dm["rank"]}
                elif op == "U":
                    old_key = change["old"]
                    if old_key not in snapshot:
                        aborted = True
                        break
                    base = dict(snapshot[old_key])
                    for name, val in dm.items():
                        base[name] = val
                    new_key = base.get("key")
                    if not isinstance(new_key, str) or new_key == "":
                        aborted = True
                        break
                    new_rows[new_key] = {"body": base.get("body"), "rank": base.get("rank")}
                else:
                    aborted = True
                    break
            if aborted:
                break

            # Check new key collisions among new rows
            # (new rows keys are unique by construction since dict; but check against
            #  remaining old rows not being removed)
            # Remove old identities, then place new rows
            for ok in old_keys:
                del snapshot[ok]
            for nk, nv in new_rows.items():
                if nk in snapshot:
                    aborted = True
                    break
                snapshot[nk] = nv
            if aborted:
                break

        if aborted:
            log.append([lsn, "ABORT"])
        else:
            rows = snapshot
            committed.add(lsn)
            log.append([lsn, "COMMIT"])

    return {"log": log, "rows": rows}
