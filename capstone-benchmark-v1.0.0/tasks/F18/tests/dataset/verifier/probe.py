"""Isolated candidate API invocation. No golden answers enter this process."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile


def put(value,parts,data):
    if not parts:return copy.deepcopy(data)
    key=parts[0]
    if value is None:value=[] if key.isdigit() else {}
    if isinstance(value,list):
        while len(value)<=int(key):value.append(None)
        value[int(key)]=put(value[int(key)],parts[1:],data)
    else:value[key]=put(value.get(key),parts[1:],data)
    return value


def case_files(contract,payload,root):
    blobs={}
    for key,binding in contract['bindings'].items():
        name,_,fragment=binding.partition('#')
        parts=fragment.strip('/').split('/') if fragment.strip('/') else []
        blobs[name]=put(blobs.get(name),parts,payload[key])
    for name,value in blobs.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    return blobs


def run(job):
    root=Path(job['workspace']).resolve();sys.path.insert(0,str(root))
    folder=root/job['folder']
    spec=importlib.util.spec_from_file_location('candidate_api',folder/'engine.py')
    api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
    contract=job['contract'];payload=copy.deepcopy(job['payload'])
    if job['kind']=='transform':
        original=copy.deepcopy(payload)
        original_contract=copy.deepcopy(contract)
        value=api.transform(payload,contract)
        unchanged=payload==original and contract==original_contract
        stored=copy.deepcopy(value)
        if contract['task'] in ('N02','N02-M2'):
            # Metadata alias isolation is the source bug's actual business rule.
            def perturb(node):
                if isinstance(node,dict):
                    for key,item in list(node.items()):
                        if key in ('dims','coords') and isinstance(item,list):item.append('__alias_probe__')
                        elif key in ('attrs','indexes') and isinstance(item,dict):item['__alias_probe__']=True
                        else:perturb(item)
                elif isinstance(node,list):
                    for item in node:perturb(item)
            perturb(value);unchanged=unchanged and payload==original
        return dict(ok=True,value=stored,input_unchanged=unchanged)
    with tempfile.TemporaryDirectory(prefix='medium30-clean-build-') as td:
        fresh=Path(td)
        blobs=case_files(contract,payload,fresh)
        loads=[]
        for name,data in blobs.items():loads.append(api.load_payload(fresh/name)==data)
        value=api.build_component(fresh,contract)
        output=fresh/contract['output'];stored=json.loads(output.read_text(encoding='utf-8')) if output.is_file() else None
        emitted={}
        for name,item in contract.get('emit',{}).items():
            target=fresh/name
            if not target.exists():emitted[name]=None
            elif item['format']=='text':emitted[name]=target.read_text(encoding='utf-8')
            elif item['format']=='json':emitted[name]=json.loads(target.read_text(encoding='utf-8'))
            elif item['format']=='ics':
                from semantic import ics_record
                emitted[name]=ics_record(target.read_text(encoding='utf-8'))
            elif item['format']=='base64':
                import base64
                emitted[name]=base64.b64encode(target.read_bytes()).decode()
            elif item['format']=='tree-base64':
                import base64
                emitted[name]={x.relative_to(target).as_posix():base64.b64encode(x.read_bytes()).decode() for x in target.rglob('*') if x.is_file()}
            elif item['format']=='npy':
                import numpy as np
                emitted[name]=np.load(target,allow_pickle=False).tolist()
        return dict(ok=True,value=value,stored=stored,loads=loads,emitted=emitted,clean_root=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--job',required=True);parser.add_argument('--out',required=True);a=parser.parse_args()
    try:
        result=run(json.loads(Path(a.job).read_text(encoding='utf-8')))
        # Enforce the declared JSON interface, not defensive checks on unused fields.
        text=json.dumps(result,ensure_ascii=False,allow_nan=False)
    except Exception as error:text=json.dumps(dict(ok=False,error=type(error).__name__,detail=str(error)[:500]),ensure_ascii=False)
    Path(a.out).write_text(text,encoding='utf-8')
