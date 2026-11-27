"""Verify the exported statistics and file bytes, offline with Python stdlib."""
from pathlib import Path
from hashlib import sha256
from decimal import Decimal
from collections import Counter
import csv
import json
import math
import statistics
import zipfile
from workspace_reward import task_reward, POLICY_SHA256

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / 'comparison.json').read_text(encoding='utf-8'))
assert data['policy_sha256'] == POLICY_SHA256
assert len(data['rows']) == 236 and len(data['pairs']) == 118
identities = {(r['provider'], r['planning_limit'], r['task_id']) for r in data['rows']}
assert len(identities) == 236
index = {(r['provider'], r['planning_limit'], r['task_id']): r for r in data['rows']}
assert data['provider_requests_in_analysis'] == 0
for row in data['rows']:
    result = task_reward(difficulty=row['reward_difficulty'], passed=row['registered_passed'],
        total=row['registered_total'], strict_pass=row['strict_pass'], integrity_ok=row['integrity_ok'])
    assert result == Decimal(str(row['reward'])), ('reward', row['task_id'])
    assert row['total_tokens'] == row['input_tokens'] + row['output_tokens']
    assert row['empty_graph'] == (row['seed_tasks'] == 0)
    assert row['planning_turns'] <= row['planning_limit']
    cost = ((row['input_tokens']-row['cache_tokens'])*1.32 + row['cache_tokens']*.044 + row['output_tokens']*3.96)/1e6 if row['provider']=='deepseek' else (row['input_tokens']*12+row['output_tokens']*36)/1e6
    assert math.isclose(cost, row['cost_comparison'], rel_tol=1e-12, abs_tol=1e-10)
for summary in data['summaries']:
    rows = [r for r in data['rows'] if (r['provider'],r['planning_limit']) == (summary['provider'],summary['planning_limit'])]
    assert len(rows) == 59
    assert sum(r['registered_total'] for r in rows) == 1217
    assert sum(r['max_reward'] for r in rows) == 138
    assert sum(r['api_total'] for r in rows) == summary['api_total'] == 803
    assert sum(r['api_passed'] for r in rows) == summary['api_passed']
    assert sum(r['strict_pass'] for r in rows) == summary['strict_passed']
    assert sum(r['empty_graph'] for r in rows) == summary['empty_graph']
    assert sum(Decimal(str(r['reward'])) for r in rows) == Decimal(str(summary['reward']))
    for field in ('input_tokens','output_tokens','total_tokens','cost_comparison'):
        assert math.isclose(sum(r[field] for r in rows), summary[field], abs_tol=1e-8)
    assert math.isclose(statistics.mean(r['e2e_seconds'] for r in rows), summary['mean_e2e_seconds'], abs_tol=1e-8)
for pair in data['pairs']:
    for side, limit in [('before',5),('after',20)]:
        row = index[pair['provider'],limit,pair['task_id']]
        for key in ('reward','strict_pass','api_passed','api_total','e2e_seconds','total_tokens','trial_id'):
            assert pair[side][key] == row[key]
for transition in data['transitions']:
    pairs = [p for p in data['pairs'] if p['provider']==transition['provider']]
    assert len(pairs)==59
    for field in ('graph','strict'):
        assert dict(Counter(p[field+'_transition'] for p in pairs)) == transition[field]
for name, count in [('trials236.csv',236),('paired118.csv',118),('summary4.csv',4)]:
    with (ROOT / name).open(encoding='utf-8-sig',newline='') as handle:
        assert len(list(csv.DictReader(handle))) == count
trace=json.loads((ROOT/'trace-mechanisms.json').read_text(encoding='utf-8'))
assert len(trace['rows'])==354 and trace['provider_requests']==0
for s in trace['summary']:
    rows=[r for r in trace['rows'] if (r['provider'],r['planning_limit'])==(s['provider'],s['limit'])]
    assert len(rows)==s['n']==59
    assert sum(r['malformed_tool_call_prefix_replies']>0 for r in rows)==s['malformed_prefix_cells']
    assert sum(r['event_counts'].get('edit_file',0) for r in rows)==s['actual_edit_events']
    assert sum(r['event_counts'].get('round_start',0)>=100 for r in rows)==s['round100']
glm=json.loads((ROOT/'glm59-paired-supplement.json').read_text(encoding='utf-8'))
assert len(glm)==59 and len({p['task'] for p in glm})==59
for side in ['old','plan20']:
    a=[p[side] for p in glm]
    assert sum(r['api_total'] for r in a)==803
    assert sum(r['core_total'] for r in a)==1217
    for r in a:
        v=task_reward(difficulty=r['difficulty'],passed=r['core_passed'],total=r['core_total'],strict_pass=r['strict_pass'],integrity_ok=r['integrity_ok'])
        assert v==Decimal(str(r['reward']))
replay=json.loads((ROOT/'offline-protocol-replay.json').read_text(encoding='utf-8'))
assert replay['passed'] and replay['provider_requests']==0
assert len({r['parser_sha256'] for r in replay['images']})==1
assert len({r['base_agent_sha256'] for r in replay['images']})==1
assert replay['latte_plain_user_feedback_completed_turns']==0
checked = 0
for line in (ROOT / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
    expected, name = line.split('  ',1)
    assert sha256((ROOT / name).read_bytes()).hexdigest() == expected, ('sha256',name)
    checked += 1
with zipfile.ZipFile(ROOT / 'report-bundle.zip') as archive:
    assert archive.testzip() is None
print(json.dumps({'passed':True,'rows':236,'pairs':118,'groups':4,'reward_verified':236,
    'supplementary_glm_rewards_verified':118,'trace_rows':354,
    'file_hashes_verified':checked,'zip_crc':'passed','provider_requests':0},ensure_ascii=False))
