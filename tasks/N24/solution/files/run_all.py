from pathlib import Path
import json
from runtime import read,module

def main():
 root=Path(__file__).resolve().parent
 delivery=read(root/'delivery.json')
 pending={read(p)['name']:(p.parent.relative_to(root).as_posix(),read(p)) for p in root.rglob('contract.json')}
 results={}
 while pending:
  ready=[name for name,(folder,c) in pending.items() if all((root/b.partition('#')[0]).is_file() for b in c['bindings'].values())]
  if not ready:raise RuntimeError('Unresolved input dependencies')
  for name in sorted(ready,reverse=True):
   folder,c=pending.pop(name);results[name]=module(root,folder+'/engine.py').build_component(root,c)
 report={'task':delivery['task'],'results':results,'result':read(root/delivery['result_file'])}
 out=root/delivery['report'];out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,allow_nan=False),encoding='utf-8')

if __name__=='__main__':main()
