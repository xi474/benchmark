"""Offline public arithmetic, provenance, privacy and integrity checks. No network."""
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import collections,csv,hashlib,json,math,re,statistics
ROOT=Path(__file__).resolve().parent
read=lambda n:json.loads((ROOT/n).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-10),(a,b)
m=read('metrics.json');cells=m['cells'];usage=read('request-usage.json')
assert len(cells)==m['paid_attempts_finished']==m['authorized_attempts']==12
assert len({c['trial_id'] for c in cells})==12
assert {(c['task_index'],c['condition'],c['replicate']) for c in cells}=={
    (t,a,r) for t in [0,2] for a in ['single','multi'] for r in [1,2,3]}
assert sum(c['quality_eligible'] for c in cells)==8
assert all((c['stage']!=1)==c['quality_eligible'] for c in cells)
assert len(usage)==len({r['request_id'] for r in usage})==192
for q in usage:
    assert q['requested_model']==q['returned_model']=='deepseek-v4-pro' and q['thinking_type']=='disabled'
    assert datetime.fromisoformat(q['sent_at_utc']).date().isoformat()=='2026-11-15'
    assert datetime.fromisoformat(q['sent_at_utc']).weekday()==6
    assert q['schedule_multiplier']==.5 and q['cost_is_invoice'] is False
    hit=q['billing_cache_tokens'];assert 0<=hit<=q['input_tokens']
    value=(Decimal(q['input_tokens']-hit)*Decimal('1.32')+Decimal(hit)*Decimal('.044')+
           Decimal(q['output_tokens'])*Decimal('3.96'))/Decimal(1000000)
    close(value,q['estimated_peak_usd']);close(value/2,q['estimated_weekend_usd'])
for c in cells:
    rows=[q for q in usage if q['trial_id']==c['trial_id']]
    assert len(rows)==c['requests']==c['ledger']['sent']==c['ledger']['settled']
    assert c['ledger']['unknown']==0 and c['agent_exception'] is None
    for k in ['input_tokens','output_tokens','cache_tokens','billing_cache_tokens']:
        assert sum(q[k] for q in rows)==c[k]
    assert c['input_tokens']+c['output_tokens']==c['total_tokens']
    close(sum(q['estimated_peak_usd'] for q in rows),c['estimated_peak_usd'])
    close(sum(q['estimated_weekend_usd'] for q in rows),c['estimated_weekend_usd'])
    for role,v in c['role_usage'].items():
        qs=[q for q in rows if q['role']==role]
        assert len(qs)==v['requests']
        for k in ['input_tokens','output_tokens','cache_tokens','billing_cache_tokens']:assert sum(q[k] for q in qs)==v[k]
        close(sum(q['estimated_peak_usd'] for q in qs),v['estimated_peak_usd'])
    assert c['original_api_semantic_accuracy'] is None
    assert c['e2e_sec']>=c['agent_sec']>0
    if c['stage']==3:
        assert c['original_reward']==1 and c['monitoring_gate'] and c['scoring_gate'] and c['condition_gate']
        assert c['child_count']==(0 if c['condition']=='single' else 2)
        assert c['children_with_business_work']==c['child_count']
        assert c['delegation_checkpoint_denials']==0
    else:assert c['child_count']==0
for g in m['groups']:
    rows=[c for c in cells if c['condition_version']==g['condition_version'] and c['condition']==g['condition']]
    assert g['n']==len(rows)==2
    close(g['e2e_mean_sec'],statistics.mean(c['e2e_sec'] for c in rows))
    assert g['total_tokens']==sum(c['total_tokens'] for c in rows)
    assert g['task_successes']==sum(c['original_reward']==1 for c in rows)
    assert g['quality_eligible']==all(c['quality_eligible'] for c in rows)
    for key in ['estimated_peak_usd','estimated_weekend_usd']:close(g[key],sum(c[key] for c in rows))
for s in read('stage-audits.json'):
    l=s['ledger'];assert l['sent_count']==l['complete_count'] and l['unknown_count']==l['active_request_count']==0
    assert l['reserved_peak_usd']==0 and s['supervisor_returncode']==0 and s['frozen_drift']==0
    assert s['mechanism_fixture']['passed'] and s['mechanism_fixture']['provider_requests']==0
    assert s['mechanism_fixture']['network']=='none'
assert [s['original_pilot_evidence']['passed'] for s in read('stage-audits.json')]==[False,False,True]
native=read('native-evidence-summary.json');assert len(native)==12
children=[c for n in native for c in n['children']];assert len(children)==4
assert all(c['native_model_steps']>0 and c['completed_tools']>0 and c['parent_receipts']>0 for c in children)
assert all(c['exact_parent_request_match'] is None for c in children)
caps=read('capability-snapshots.json');assert len(caps)==12
for n in caps:
    assert n['exact_root_policy_presence_verified'] and n['actual_tool_schema_hashes']
    assert ('spawn_teammate' in n['actual_tool_names'])==n['configured']['delegation_enabled']
    assert n['configured']['real_provider_key_in_container'] is False
trace=read('native-timeline-data.json');assert len(trace['cells'])==4 and trace['new_model_requests']==0
assert sum(len(c['intervals']) for c in trace['cells'])==88
assert sum(c['http_wait_wall_union_sec'] for c in trace['cells'])>0
pairs=read('parallel-trace-summary.json')
for c in pairs['cells']:
    if c['condition']=='multi':
        assert c['parent_receipts']==4
        assert any(x['roles']==['child1','child2'] and x['actual_http_overlap_sec']>0 for x in c['actual_http_role_overlaps'])
d=read('analysis-data.json');S=d['groups']['single'];M=d['groups']['multi']
assert S['total_tokens']==663716 and M['total_tokens']==898067
assert sum(d['extra_token_roles'].values())==M['total_tokens']-S['total_tokens']
close(sum(v['delta_usd'] for v in d['extra_cost_components'].values()),M['cost_weekend_usd']-S['cost_weekend_usd'])
close(sum(q['estimated_peak_usd'] for q in usage),.528690096)
close(sum(q['estimated_weekend_usd'] for q in usage),.264345048)
audit=read('completion-audit.json');assert audit['future_admission_closed'] and audit['frozen_drift']==0
assert audit['unknown']==audit['active_requests']==0 and audit['paid_retries']==0
assert sha(ROOT/'metrics.json')==read('provenance.json')['source_metrics_sha256']
assert len(list((ROOT/'figures').glob('*.png')))==len(list((ROOT/'figures').glob('*.svg')))==5
assert read('canvas-validation.json')['errors']==[]
for name,n in [('cells.csv',12),('groups.csv',6),('request-usage.csv',192),('cost-components.csv',6)]:
    with (ROOT/name).open(encoding='utf-8-sig',newline='') as f:assert len(list(csv.DictReader(f)))==n
manifest=read('artifact-manifest.json')['sha256']
actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name!='artifact-manifest.json' and '__pycache__' not in p.parts}
assert set(manifest)==actual
for n,h in manifest.items():
    p=(ROOT/n).resolve();assert p.is_relative_to(ROOT.resolve()) and sha(p)==h,n
for p in ROOT.rglob('*'):
    if not p.is_file() or p.suffix not in ['.md','.json','.py','.csv','.svg','.tsx']:continue
    s=p.read_text(encoding='utf-8-sig')
    for i,pattern in enumerate([r'(?i)\bsk-[a-z0-9_-]{16,}',r'(?i)Bearer\s+[a-z0-9._-]{16,}',
                               r'[A-Z]:[\\/]Users[\\/]',r'/home/[A-Za-z0-9_-]+/',r'/mnt/[a-z]/Users/']):
        assert not re.search(pattern,s),f'{p.name}: forbidden sensitive pattern {i}'
for target in re.findall(r'\]\(([^)]+)\)',(ROOT/'README.md').read_text(encoding='utf-8')):
    if not target.startswith(('https://','http://','#')):assert (ROOT/target.split('#')[0]).exists(),target
print(json.dumps(dict(passed=True,attempts=12,quality_eligible=8,censored=4,settled_requests=192,unknown=0,
    strict_working_children=4,figures_png=5,figures_svg=5,public_files_hashed=len(manifest),model_calls=0)))
