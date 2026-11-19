import copy, importlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(Path(__file__).resolve().parent))
from model import load_payload
from transform import transform
from render import build_component

def main():
    cp=Path(__file__).with_name('contract.json'); c=load_payload(cp)
    payloads=[load_payload(ROOT/p) for p in c['inputs']]; before=copy.deepcopy(payloads); cc=copy.deepcopy(c)
    result=transform(payloads,c)
    assert payloads==before and c==cc,'inputs/contract mutated'
    assert type(result) is dict and set(result)=={'name','result'} and result['name']==c['name'] and type(result['result']) is dict
    assert build_component(ROOT,cp)==result
    assert json.loads((ROOT/c['output']).read_text(encoding='utf-8'))==result
    pass
    print('MODULE_OK',c['name'])
if __name__=='__main__': main()
