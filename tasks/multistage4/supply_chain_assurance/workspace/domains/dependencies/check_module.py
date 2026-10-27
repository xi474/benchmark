from __future__ import annotations
import json
from pathlib import Path
from parse import load_records
from normalize import normalize_records
from analyze import build_summary
from render import build_evidence

ROOT=Path(__file__).resolve().parents[2]
CONTRACT=json.loads((Path(__file__).with_name('contract.json')).read_text(encoding='utf-8'))
ROWS=load_records(ROOT/CONTRACT['input'])
NORMAL=normalize_records(ROWS,CONTRACT)
assert NORMAL == sorted(NORMAL,key=lambda r:r['id'])
assert all(set(r)=={'id','category','score','owner','tags'} for r in NORMAL)
assert all(0 <= r['score'] <= 20 for r in NORMAL)
SUMMARY=build_summary(NORMAL,CONTRACT['high_threshold'])
assert SUMMARY['count']==len(NORMAL)
assert SUMMARY['score_total']==sum(r['score'] for r in NORMAL)
EVIDENCE=build_evidence(ROOT/CONTRACT['input'],Path(__file__).with_name('contract.json'))
assert EVIDENCE=={'domain':'dependencies','records':NORMAL,'summary':SUMMARY}
print('MODULE_OK dependencies')
