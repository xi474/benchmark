import json
from pathlib import Path
from model import load_payload
from transform import transform
ROOT=Path(__file__).resolve().parents[1]

def build_component(root,contract_path):
    root=Path(root); c=load_payload(Path(contract_path))
    return transform([load_payload(root/p) for p in c['inputs']],c)

if __name__=='__main__':
    cp=Path(__file__).with_name('contract.json'); c=load_payload(cp)
    value=build_component(ROOT,cp); out=ROOT/c['output']; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')
