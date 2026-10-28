"""Trusted API probe. Input payloads go to candidate code; golden values do not."""
import contextlib
import copy
import importlib
import io
import json
import sys
import tempfile
from pathlib import Path

def main():
    folder=Path(sys.argv[1]).resolve(); suite=sys.argv[2]
    packet=json.loads(sys.stdin.read()); responses=[]
    sys.path.insert(0,str(folder))
    with contextlib.redirect_stdout(io.StringIO()):
        module=importlib.import_module('transform')
        model=importlib.import_module('model')
        with tempfile.TemporaryDirectory(prefix='mixed16-probe-json-',dir=folder.parents[1]) as tmp:
            for content in ('7','null','"text"','{bad'):
                p=Path(tmp)/'invalid.json'; p.write_text(content,encoding='utf-8')
                try: model.load_payload(p)
                except ValueError: pass
                else: raise AssertionError('model must reject invalid top-level JSON')
        for case in packet['cases']:
            payloads=copy.deepcopy(case['payloads']); c=copy.deepcopy(case['contract'])
            # Compare serialized inputs because NaN is not equal to itself.
            before=json.dumps([payloads,c],sort_keys=True)
            try:
                value=module.transform(payloads,c)
                assert json.dumps([payloads,c],sort_keys=True)==before,'input mutation'
                json.dumps(value,allow_nan=False)
                responses.append(dict(kind='value',value=value))
            except ValueError: responses.append(dict(kind='ValueError'))
            except Exception as exc: responses.append(dict(kind=type(exc).__name__,error=str(exc)))
        if suite=='context8':
            sys.path.insert(0,str(folder.parent))
            parser=importlib.import_module(folder.name+'.parser')
            case=packet['cases'][0]
            assert parser.parse(copy.deepcopy(case['payloads']),copy.deepcopy(case['contract']))==module.transform(copy.deepcopy(case['payloads']),copy.deepcopy(case['contract']))
    print(json.dumps(responses,ensure_ascii=False,allow_nan=False))

if __name__=='__main__': main()
