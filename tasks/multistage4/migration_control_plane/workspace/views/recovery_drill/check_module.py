from __future__ import annotations
import json
from pathlib import Path
from filter_records import select_records
from summarize import summarize_records
from render import build_view

ROOT=Path(__file__).resolve().parents[2]
CONTRACT=json.loads((Path(__file__).with_name('contract.json')).read_text(encoding='utf-8'))
CORE=json.loads((ROOT/'outputs/core_manifest.json').read_text(encoding='utf-8'))
ROWS=select_records(CORE,CONTRACT)
assert ROWS==sorted(ROWS,key=lambda r:(-r['score'],r['source'],r['id']))
SUMMARY=summarize_records(ROWS)
assert SUMMARY['count']==len(ROWS)
VIEW=build_view(ROOT/'outputs/core_manifest.json',Path(__file__).with_name('contract.json'))
assert VIEW['view']=='recovery_drill' and VIEW['count']==len(ROWS)
print('VIEW_OK recovery_drill')
