"""One isolated existing API vector or I/O bundle; no oracle data is passed here."""
import contextlib,copy,importlib,io,json,os,sys,tempfile
from pathlib import Path

def api(request):
    case=request['case'];payloads=copy.deepcopy(case['payloads']);contract=copy.deepcopy(case['contract']);before=json.dumps([payloads,contract],sort_keys=True);transform=importlib.import_module('transform').transform
    try:
        value=transform(payloads,contract)
        assert json.dumps([payloads,contract],sort_keys=True)==before,'input mutation'
        if request['flavor']=='medium':
            assert type(value) is dict and set(value)=={'name','result'} and value['name']==contract['name'] and type(value['result']) is dict,'bad wrapper'
            if request['suite']=='context8':
                package=importlib.import_module(request['folder']+'.parser');assert package.parse(copy.deepcopy(case['payloads']),copy.deepcopy(case['contract']))==value,'parser API mismatch'
    except ValueError:return dict(kind='ValueError')
    except Exception as exc:return dict(kind='exception',type=type(exc).__name__,message=str(exc))
    try:json.dumps(value,allow_nan=False)
    except (ValueError,TypeError):return dict(kind='exception',type='InvalidReturn',message='result is not finite JSON')
    return dict(kind='value',value=value)

def io_bundle(request):
    model=importlib.import_module('model');passed=[];details={};flavor=request['flavor'];case=request['case']
    cases=[('{}',True),('[]',True),('null',False),('false',False),('3',False),('"x"',False),('{broken',False),('{"ignored":NaN}',False)] if flavor=='medium' else [('7',False),('null',False),('"text"',False),('{bad',False)]
    with tempfile.TemporaryDirectory(prefix='reward-io-',dir=os.environ.get('REWARD_V2_TMP')) as temporary:
        root=Path(temporary)
        for i,(source,valid) in enumerate(cases):
            p=root/f'{i}.json';p.write_text(source,encoding='utf-8')
            try:value=model.load_payload(p);ok=valid and value==json.loads(source)
            except ValueError:ok=not valid
            except Exception:ok=False
            passed.append(ok)
        details['loader_cases']=passed
        transform=importlib.import_module('transform').transform
        if flavor=='medium':
            render=importlib.import_module('render');contract=copy.deepcopy(case['contract']);contract['inputs']=[]
            for i,payload in enumerate(case['payloads']):
                rel=f'input-{i}.json';(root/rel).write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8');contract['inputs'].append(rel)
            cp=root/'contract.json';cp.write_text(json.dumps(contract),encoding='utf-8')
            try:details['render']=render.build_component(root,cp)==transform(copy.deepcopy(case['payloads']),copy.deepcopy(contract))
            except Exception:details['render']=False
        if request['suite']=='context8':
            try:package=importlib.import_module(request['folder']+'.parser');details['parser']=package.parse(copy.deepcopy(case['payloads']),copy.deepcopy(case['contract']))==transform(copy.deepcopy(case['payloads']),copy.deepcopy(case['contract']))
            except Exception:details['parser']=False
    return dict(kind='io',passed=all(passed) and all(v for k,v in details.items() if k!='loader_cases'),details=details)

def main():
    request=json.loads(sys.stdin.read());workspace=Path(request['workspace']).resolve();sys.path.insert(0,str(workspace));sys.path.insert(0,str(workspace/request['folder']));sys.dont_write_bytecode=True
    try:
        stream=contextlib.redirect_stdout(io.StringIO()) if request['flavor']=='hard' else contextlib.nullcontext()
        with stream:response=api(request) if request['kind']=='api' else io_bundle(request)
    except Exception as exc:response=dict(kind='exception',type=type(exc).__name__,message=str(exc))
    print(json.dumps(response,ensure_ascii=False,allow_nan=False))
if __name__=='__main__':main()
