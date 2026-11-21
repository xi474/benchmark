def combine(p, left, right):
    committed=set()
    rows=dict(p["initial"])
    log=[]
    for ti,tx in enumerate(p["txs"]):
        seq=tx["lsn"]
        if seq in committed:
            log.append([seq,"REPLAY"])
            continue
        current=rows.copy()
        try:
            for si,statement in enumerate(tx["statements"]):
                consumed=set(left[ti][si])
                if consumed-current.keys():
                    raise ValueError("identity")
                after={k:v for k,v in current.items() if k not in consumed}
                for mi,m in enumerate(statement):
                    if m["op"]=="D":
                        continue
                    data={"key":m.get("old"),**current.get(m.get("old"),{})}
                    decoded=right[ti][si][mi]
                    if decoded is None:raise ValueError('type')
                    data.update(decoded)
                    key=data.pop("key")
                    if key in after:
                        raise ValueError("collision")
                    after[key]=data
                current=after
        except ValueError:
            status="ABORT"
        else:
            rows=current
            committed.add(seq)
            status="COMMIT"
        log.append([seq,status])
    return dict(rows=rows,log=log)

from pathlib import Path
import json

