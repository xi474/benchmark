#!/bin/bash
set -eu
cd /app
cat > solution.py <<'MEDIUM69_REFERENCE'
def transform(p):
    nodes=p["nodes"].copy()
    idx=p["initial"].copy()
    report=[]
    for scan in p["scans"]:
        nodes.update(scan["replace"])
        previous=idx.copy()
        for path in sorted(scan["finish"],key=lambda v:v.count("/")):
            parts=path.split("/")
            node=nodes[p["mounts"][parts[0]]]
            for child in parts[1:]:
                node=nodes[node["dirs"][child]]
            ignore=set(node["ignore"])
            files={k:v for k,v in node["files"].items() if k not in ignore}
            dirs=set(node["dirs"])-ignore
            prefix=path+"/"
            for key in list(idx):
                if not key.startswith(prefix):continue
                relative=key[len(prefix):]
                first,slash,_=relative.partition("/")
                if (slash and first not in dirs) or (not slash and first not in files):
                    del idx[key]
            idx.update({prefix+name:ident for name,ident in files.items()})
        def reverse(mapping):
            result={}
            for name,ident in sorted(mapping.items()):
                result.setdefault(ident,[]).append(name)
            return result
        left,right=reverse(previous),reverse(idx)
        changes={k:[left.get(k,[]),right.get(k,[])] for k in left.keys()|right.keys() if left.get(k)!=right.get(k)}
        report.append(dict(index=idx.copy(),changed=changes))
    return report

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
