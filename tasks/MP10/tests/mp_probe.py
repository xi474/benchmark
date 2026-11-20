"""Candidate-side invocation. No expected answer or reward metadata is supplied."""
import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile


def run(q):
    case=q["case"]
    payloads,contract=copy.deepcopy(case["payloads"]),copy.deepcopy(case["contract"])
    workspace=Path.cwd()
    sys.path[:0]=[str(workspace/q["folder"]),str(workspace)]
    if q["kind"]=="api":
        try:
            result=importlib.import_module("transform").transform(payloads,contract)
        except ValueError:
            if payloads!=case["payloads"] or contract!=case["contract"]:
                raise RuntimeError("input mutation")
            return {"kind":"ValueError"}
        assert payloads==case["payloads"] and contract==case["contract"]
        return {"kind":"value","value":result}
    load=importlib.import_module("model").load_payload
    build=importlib.import_module("render").build_component
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        contract["inputs"]=[]
        for i,payload in enumerate(payloads):
            rel=f"source-{i}.json"
            (root/rel).write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
            assert load(root/rel)==payload
            contract["inputs"].append(rel)
        cp=root/"contract.json"
        cp.write_text(json.dumps(contract,ensure_ascii=False),encoding="utf-8")
        assert load(cp)==contract
        result=build(root,cp)
        if q["suite"]=="context8":
            parser=importlib.import_module(q["folder"]+".parser")
            assert parser.parse(copy.deepcopy(case["payloads"]),copy.deepcopy(case["contract"]))==result
    return {"kind":"value","value":result}


if __name__=="__main__":
    print(json.dumps(run(json.load(sys.stdin)),allow_nan=False))
