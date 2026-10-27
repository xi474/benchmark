from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DOMAIN_ROOT=ROOT/'domains'
evidence=[]
for directory in sorted(p for p in DOMAIN_ROOT.iterdir() if p.is_dir()):
    contract=json.loads((directory/'contract.json').read_text(encoding='utf-8'))
    path=ROOT/contract['output']
    if not path.is_file(): raise SystemExit(f'missing evidence: {path.relative_to(ROOT)}')
    payload=json.loads(path.read_text(encoding='utf-8'))
    if payload.get('domain') != contract['domain']: raise SystemExit(f'domain mismatch: {path}')
    evidence.append(payload)
records=[]; summaries={}
for payload in evidence:
    name=payload['domain']; summaries[name]=payload['summary']
    records.extend({**row,'source':name} for row in payload['records'])
records.sort(key=lambda r:(r['source'],r['id']))
core={'record_count':len(records),'score_total':sum(r['score'] for r in records),
      'sources':sorted(summaries),'domain_summaries':dict(sorted(summaries.items())),'records':records}
out=ROOT/'outputs/core_manifest.json'; out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(core,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(out.relative_to(ROOT))
