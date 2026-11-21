"""Forensic single-row J1 replay: save full assistant responses for 5 representative
C/MS handshake inputs to diagnose why the J1 prompt did not open frontier widths."""

import json
import pathlib
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from j1_replay import patch_row, call_model  # reuse the exact J1 patch

PLAN = json.loads((HERE / 'experiment_plan.json').read_text(encoding='utf-8-sig'))
PROFILE = PLAN['arms']['on']['backend']
sys.path.insert(0, str(ROOT))
from user_api_credential import user_api_key
KEY = user_api_key(PROFILE['credential_source_user_thread'], PROFILE['credential_fingerprint'])

SAMPLES = [
    ('C008', 'context8/C008', 0),
    ('C069', 'context8/C069', 0),
    ('C017', 'context8/C017', 0),
    ('C066', 'context8/C066', 1),
    ('MS02', 'context8/MS02', 0),
]

out_path = HERE / 'j1_forensic.json'
rows = []
for tid, entry, index in SAMPLES:
    path = HERE / 'online' / 'on' / 'cases' / entry / 'dynamic_v7' / 'handshake_inputs.jsonl'
    data = [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]
    row = data[index]
    messages, tools = patch_row(row)
    response = call_model(messages, tools, KEY, row['model'])
    message = response['choices'][0]['message']
    record = dict(task_id=tid, index=index, step=row.get('step'),
                  finish_reason=response['choices'][0].get('finish_reason'),
                  narration=message.get('content'),
                  tool_calls=[],
                  usage=response.get('usage'))
    for tc in (message.get('tool_calls') or []):
        fn = tc.get('function') or {}
        try:
            args = json.loads(fn.get('arguments') or '{}')
        except Exception:
            args = {'_raw': fn.get('arguments')}
        record['tool_calls'].append(dict(name=fn.get('name'), args=args))
    rows.append(record)
    print('FORENSIC', tid, 'step', row.get('step'),
          'units=', len((record['tool_calls'][0]['args'].get('ready_upsert') or [])
                        if record['tool_calls'] and record['tool_calls'][0]['name'] == 'report_frontier_state' else []),
          flush=True)
out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
print('WROTE', out_path)
