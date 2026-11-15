"""Offline arithmetic/integrity audit; no network, model calls, or data edits."""
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import collections,csv,hashlib,json,math,re,statistics
ROOT=Path(__file__).resolve().parent
def read(n):return json.loads((ROOT/n).read_text(encoding='utf-8'))
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-9),(a,b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=read('metrics.json');cells=m['cells'];usage=read('request-usage.json');checks=read('functional-checks.json')
assert m['completed'] and len(cells)==12 and len({c['trial_id'] for c in cells})==12
assert {(c['task_id'],c['condition'],c['replicate']) for c in cells}=={(t,a,r) for t in ['TP','DBG'] for a in ['single','multi'] for r in [1,2,3]}
assert len(usage)==len({r['request_id'] for r in usage})==288
assert all(r['model']=='deepseek-v4-pro' and r['thinking_type']=='disabled' for r in usage)
assert len(checks)==len({(r['trial_id'],r['id']) for r in checks})==498
assert sum(r['state']=='passed' for r in checks)==434
costs=collections.defaultdict(lambda:Decimal(0));peak=collections.defaultdict(lambda:Decimal(0))
for r in usage:
 dt=datetime.fromisoformat(r['sent_at_utc']);assert dt.weekday()==6 and dt.date().isoformat()=='2026-11-15'
 assert r['schedule_multiplier']==.5 and r['cache_tokens'] is not None
 cache=r['billing_cache_tokens'];assert 0<=cache<=r['input_tokens']
 value=(Decimal(r['input_tokens']-cache)*Decimal('1.32')+Decimal(cache)*Decimal('.044')+Decimal(r['output_tokens'])*Decimal('3.96'))/Decimal(1000000)
 close(value,r['estimated_peak_usd']);close(value/2,r['estimated_provider_schedule_usd'])
 costs[r['trial_id']]+=value/2;peak[r['trial_id']]+=value
for c in cells:
 rs=[r for r in usage if r['trial_id']==c['trial_id']];cs=[r for r in checks if r['trial_id']==c['trial_id']]
 assert len(rs)==c['requests'];assert len(cs)==c['total']==(50 if c['task_id']=='TP' else 33)
 assert sum(r['state']=='passed' for r in cs)==c['passed'];close(c['passed']/c['total'],c['accuracy'])
 assert sum(r['input_tokens'] for r in rs)==c['input_tokens'];assert sum(r['output_tokens'] for r in rs)==c['output_tokens']
 assert c['input_tokens']+c['output_tokens']==c['total_tokens']
 close(costs[c['trial_id']],c['estimated_provider_schedule_usd']);close(peak[c['trial_id']],c['estimated_peak_usd'])
 assert not c['agent_exception'] and c['cell_stop_reason'] is None and c['incomplete_spans']==0 and c['pilot_passed']
 assert c['e2e_sec']>=c['agent_sec']>=0
 assert c['child_count']==c['children_with_work']==(0 if c['condition']=='single' else 2)
 assert c['parent_receipts']==(0 if c['condition']=='single' else 2)
for g in m['groups']:
 rs=[c for c in cells if c['condition']==g['condition'] and (g['task_id']=='ALL' or g['task_id']==c['task_id'])]
 assert g['n']==len(rs);close(g['accuracy_mean'],statistics.mean(c['accuracy'] for c in rs))
 for dest,src in [('e2e_mean_sec','e2e_sec'),('agent_mean_sec','agent_sec'),('tokens_mean','total_tokens')]:close(g[dest],statistics.mean(c[src] for c in rs))
 for dest,src in [('total_tokens','total_tokens'),('test_passed','passed'),('test_total','total'),('estimated_peak_usd','estimated_peak_usd'),('estimated_provider_schedule_usd','estimated_provider_schedule_usd')]:close(g[dest],sum(c[src] for c in rs))
 assert g['task_successes']==sum(c['task_success'] for c in rs)
for d in m['contrasts']:
 s=next(g for g in m['groups'] if g['task_id']==d['task_id'] and g['condition']=='single');g=next(g for g in m['groups'] if g['task_id']==d['task_id'] and g['condition']=='multi')
 close(d['accuracy_difference_pp'],100*(g['accuracy_mean']-s['accuracy_mean']))
 for a,b in [('e2e_change_pct','e2e_mean_sec'),('tokens_change_pct','total_tokens'),('estimated_cost_change_pct','estimated_provider_schedule_usd')]:close(d[a],100*(g[b]/s[b]-1))
assert sum(c['total_tokens'] for c in cells)==4001825
assert sum(c['input_tokens'] for c in cells)==3892728 and sum(c['output_tokens'] for c in cells)==109097
close(sum(costs.values()),.422346364);close(sum(peak.values()),.844692728)
assert sum(peak.values())<36 and all(v<3 for v in peak.values())
ledger=m['ledger'];assert ledger['sent_count']==ledger['complete_count']==288 and ledger['unknown_count']==ledger['active_request_count']==0
close(ledger['settled_peak_usd'],sum(peak.values()))
native=read('native-evidence-summary.json');assert len(native)==12
children=[c for r in native for c in r['children']];assert len(children)==12
assert all(c['native_model_steps'] and c['completed_tools'] and c['parent_receipts'] for c in children)
assert all(c['exact_parent_request_match'] is None for c in children)
assert sum(c['parent_tool_call_overlap_sec']>0 for c in children)==5
audit=read('completion-audit.json');assert audit['all_trial_prompts_verified']==12 and audit['frozen_files']==112 and audit['frozen_changed']==0 and audit['grant_closed']
assert all(r['exact_native_root_and_gateway_policy_match'] for r in audit['trial_prompt_checks'])
resources=read('resources-summary.json');assert len(resources)==12 and all(r['valid_rows']>0 for r in resources)
assert len(read('native-timeline-data.json'))==24
assert len(list((ROOT/'figures').glob('*.png')))==len(list((ROOT/'figures').glob('*.svg')))==5
for filename in ['cells.csv','groups.csv','paired-contrasts.csv','request-usage.csv']:
 with (ROOT/filename).open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
 assert len(rows)=={'cells.csv':12,'groups.csv':6,'paired-contrasts.csv':6,'request-usage.csv':288}[filename]
assert sha(ROOT/'metrics.json')==read('provenance.json')['source_metrics_sha256']
manifest=read('artifact-manifest.json')
assert set(manifest['sha256'])=={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name!='artifact-manifest.json'}
for relative,digest in manifest['sha256'].items():
 p=(ROOT/relative).resolve();assert p.is_relative_to(ROOT.resolve()) and p.is_file();assert sha(p)==digest,relative
for p in ROOT.rglob('*'):
 if not p.is_file() or p.suffix not in ['.json','.csv','.md','.py','.svg']:continue
 text=p.read_text(encoding='utf-8')
 for pattern in [r'(?i)\bsk-[a-z0-9_-]{16,}',r'(?i)Bearer\s+[a-z0-9._-]{16,}',r'[A-Z]:[\\/]Users[\\/]',r'/home/[A-Za-z0-9_-]+/',r'/mnt/[a-z]/Users/[A-Za-z0-9_-]+/']:
  assert not re.search(pattern,text),p.name
readme=(ROOT/'README.md').read_text(encoding='utf-8')
for target in re.findall(r'\]\(([^)]+)\)',readme):
 if not target.startswith(('https://','http://','#')):assert (ROOT/target.split('#')[0]).exists(),target
print(json.dumps(dict(passed=True,trials=12,pairs=6,functional_checks=498,settled_requests=288,children_with_work=12,parent_receipts=12,exact_child_result_input_match='unknown',figures_png=5,figures_svg=5,estimated_schedule_usd=.422346364,public_files_hashed=len(manifest['sha256']),network_requests=0),ensure_ascii=False))
