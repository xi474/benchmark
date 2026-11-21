def compute(payload):
    """按事务、语句、行变更生成已解码的列映射。D 用空对象；类型错误用 null，使整合端按事务回滚。"""
    txs = payload["txs"]
    result = []
    for tx in txs:
        tx_rows = []
        for statement in tx["statements"]:
            stmt_rows = []
            for change in statement:
                op = change["op"]
                if op == "D":
                    stmt_rows.append({})
                    continue
                cols = change.get("cols", [])
                decoded = {}
                ok = True
                for col in cols:
                    name = col["name"]
                    ctype = col["type"]
                    value = col["value"]
                    if ctype == "text":
                        if value is not None and not isinstance(value, str):
                            ok = False
                            break
                        decoded[name] = value
                    elif ctype == "int":
                        if value is None:
                            decoded[name] = None
                        elif isinstance(value, str):
                            try:
                                decoded[name] = int(value)
                            except ValueError:
                                ok = False
                                break
                        elif isinstance(value, int) and not isinstance(value, bool):
                            decoded[name] = value
                        else:
                            ok = False
                            break
                    else:
                        ok = False
                        break
                if not ok:
                    stmt_rows.append(None)
                else:
                    stmt_rows.append(decoded)
            tx_rows.append(stmt_rows)
        result.append(tx_rows)
    return result
