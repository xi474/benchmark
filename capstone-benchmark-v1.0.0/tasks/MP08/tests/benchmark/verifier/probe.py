"""Run candidate APIs in a fresh subprocess. This is not a malicious-code sandbox."""
from __future__ import annotations
import copy, importlib, json, os, sys, tempfile
from pathlib import Path

def main():
    workspace=Path(sys.argv[1]).resolve(); folder=sys.argv[2]; suite=sys.argv[3]
    sys.path.insert(0,str(workspace)); sys.path.insert(0,str(workspace/folder))
    from model import load_payload
    from transform import transform
    from render import build_component
    package=importlib.import_module(folder+'.parser') if suite=='context8' else None
    request=json.loads(sys.stdin.read()); responses=[]
    for case in request['cases']:
        payloads=copy.deepcopy(case['payloads']); contract=copy.deepcopy(case['contract']); before=copy.deepcopy(payloads); c_before=copy.deepcopy(contract)
        try:
            value=transform(payloads,contract)
            # NaN != NaN; JSON snapshots retain the original mutation-sensitive structure.
            if json.dumps(payloads,sort_keys=True)!=json.dumps(before,sort_keys=True) or contract!=c_before:raise AssertionError('mutation')
            if type(value) is not dict or set(value)!={'name','result'} or value['name']!=contract['name'] or type(value['result']) is not dict:raise AssertionError('bad wrapper')
            if package and package.parse(copy.deepcopy(before),copy.deepcopy(c_before))!=value:raise AssertionError('parser API mismatch')
            responses.append(dict(kind='value',value=value))
        except ValueError:responses.append(dict(kind='ValueError'))
        except Exception as exc:responses.append(dict(kind='exception',type=type(exc).__name__,message=str(exc)))
    model_cases=[]
    with tempfile.TemporaryDirectory(prefix='medium26-model-',dir=os.environ.get('MEDIUM26_TMPDIR')) as tmp:
        for i,(source,valid) in enumerate([('{}',True),('[]',True),('null',False),('false',False),('3',False),('"x"',False),('{broken',False),('{"ignored":NaN}',False)]):
            path=Path(tmp)/f'{i}.json'; path.write_text(source,encoding='utf-8')
            try:
                actual=load_payload(path); passed=valid and actual==json.loads(source)
            except ValueError:passed=not valid
            except Exception:passed=False
            model_cases.append(passed)
        # Exercise build_component with different on-disk payloads, from a fresh root.
        case=next((x for x in request['cases'] if x['label'].startswith('heldout-')),None)
        render_ok=True
        if case:
            root=Path(tmp)/'root';root.mkdir();cc=copy.deepcopy(case['contract']);cc['inputs']=[]
            for i,payload in enumerate(case['payloads']):
                rel=f'input-{i}.json';(root/rel).write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8');cc['inputs'].append(rel)
            cp=root/'contract.json';cp.write_text(json.dumps(cc),encoding='utf-8')
            try:render_ok=build_component(root,cp)==transform(copy.deepcopy(case['payloads']),copy.deepcopy(cc))
            except Exception:render_ok=False
    print(json.dumps(dict(responses=responses,model_cases=model_cases,render_ok=render_ok),ensure_ascii=False,allow_nan=False))

if __name__=='__main__':main()
