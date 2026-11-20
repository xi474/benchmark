#!/bin/bash
set -eu
cd /app
cat > solution.py <<'MEDIUM69_REFERENCE'
def transform(p):
    committed=set()
    rows=dict(p["initial"])
    log=[]
    for tx in p["txs"]:
        seq=tx["lsn"]
        if seq in committed:
            log.append([seq,"REPLAY"])
            continue
        current=rows.copy()
        try:
            for statement in tx["statements"]:
                consumed={m["old"] for m in statement if m["op"]!="I"}
                if consumed-current.keys():
                    raise ValueError("identity")
                after={k:v for k,v in current.items() if k not in consumed}
                for m in statement:
                    if m["op"]=="D":
                        continue
                    data={"key":m.get("old"),**current.get(m.get("old"),{})}
                    for col in m["cols"]:
                        key,typ,v=col["name"],col["type"],col["value"]
                        if typ!=("int" if key=="rank" else "text"):
                            raise ValueError("type")
                        data[key]=int(v) if key=="rank" and v is not None else v
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

def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value

MEDIUM69_REFERENCE
