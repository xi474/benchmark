"""Check the exported visible-trace audit; does not replay unpublished native sessions."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json

P=Path(__file__).resolve().parent
read=lambda path:json.loads(path.read_text(encoding='utf-8-sig'))
a=read(P/'未委派trace审计.json')
receipt=read(P/'未委派trace分析验收.json')
assert a['private_reasoning_exported'] is False and a['new_provider_calls']==0
assert len(a['rows'])==45
assert Counter(r['condition'] for r in a['rows'])=={'ordinary':20,'high-original32k':20,'high-soft-rerun':5}
assert hashlib.sha256(a['prompt'].encode()).hexdigest()==a['prompt_sha256']
current_ids=set(a['current_high_trial_ids'])
normal={r['task_id']:r for r in a['rows'] if r['condition']=='ordinary'}
high={r['task_id']:r for r in a['rows'] if r['trial_id'] in current_ids}
assert set(normal)==set(high) and len(high)==20
reruns={r['task_id'] for r in a['rows'] if r['condition']=='high-soft-rerun'}
assert reruns=={'I06','K64','L114','M103','X13'}
for ident,row in high.items():assert (row['condition']=='high-soft-rerun')==(ident in reruns)
for label,rows in [('ordinary',list(normal.values())),('high-current',list(high.values()))]:
    s=a['summary'][label]
    assert sum(bool(r['roster_calls']) for r in rows)==len(s['tasks_with_roster_calls'])
    assert sum(r['final_statements']['work decomposition']['choice']=='yes' for r in rows)==s['final_decomposition_choices']['yes']
    assert sum(r['first_statements']['subagent delegation']['before_first_observed_write_or_spawn'] is True for r in rows)==s['tasks_with_prewrite_delegation_statement']
    for row in rows:
        assert 'spawn_teammate' in row['actual_tools'] and row['actual_mode_verified']
        assert row['exact_optional_prompt_observed_in_native_user_text']
        assert row['configured']['guided_prompt_sha256'] in {None,a['prompt_sha256']}
        assert row['configured']['minimum_workers']==0
        assert not row['configured']['force_delegation'] and not row['configured']['additional_tool_guards']
        assert not row['creation_attempts'] and not row['native_nonroot_sessions']
        assert row['final_statements']['subagent delegation']['choice']=='no'
        assert not any(call['is_error'] is True for call in row['roster_calls'])
        assert row['source_native_files']
        assert all(len(source['sha256'])==64 for source in row['source_native_files'])
assert len(a['summary']['ordinary']['tasks_with_roster_calls'])==8
assert len(a['summary']['high-current']['tasks_with_roster_calls'])==18
assert a['summary']['ordinary']['final_decomposition_choices']['yes']==6
assert a['summary']['high-current']['final_decomposition_choices']['yes']==7
positive=a['additional_real_positive_control']
assert positive['task_id']=='M103'
assert len(positive['creation_attempts'])==len(positive['native_nonroot_sessions'])==2
assert all(call['complete'] and not call['is_error'] for call in positive['creation_attempts'])
with (P/'未委派理由逐题对照.csv').open(encoding='utf-8-sig',newline='') as f:csv_rows=list(csv.DictReader(f))
assert len(csv_rows)==20 and {r['task_id'] for r in csv_rows}==set(normal)
for row in csv_rows:
    ident=row['task_id']
    for prefix,source in [('ordinary',normal[ident]),('high',high[ident])]:
        assert row[prefix+'_trial_id']==source['trial_id']
        assert row[prefix+'_visible_reason']==source['final_statements']['subagent delegation']['text']
        assert row[prefix+'_decomposition']==source['final_statements']['work decomposition']['choice']
assert receipt['complete'] and receipt['private_reasoning_exported'] is False
print(json.dumps(dict(passed=True,native_trial_exports_checked=45,extra_positive_controls=1,
    reason_pairs_checked=20,current_result_rows_checked=40,new_provider_calls=0,
    independent_reparse_of_unpublished_native_logs=False)))
