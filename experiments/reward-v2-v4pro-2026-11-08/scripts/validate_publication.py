"""Validate the result-only publication offline; never calls model APIs."""
import collections,csv,hashlib,json,pathlib,re,statistics,subprocess,sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
def read_json(p):return json.loads(p.read_text(encoding='utf-8'))
def read_csv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):return abs(float(a)-float(b))<1e-7

audit=read_json(ROOT/'publication-audit.json')
assert audit['provider_requests']==0
for name,digest in audit['artifact_sha256'].items():assert sha(ROOT/name)==digest,name
subprocess.run([sys.executable,'-B',str(ROOT/'seven-harnesses/scripts/validate_release.py')],check=True)
seven=read_json(ROOT/'seven-harnesses/results.json')
aa=read_json(ROOT/'aorchestra/results-56.json'); ar=aa['rows']
assert len(ar)==56 and len({r['task'] for r in ar})==56
assert collections.Counter(r['task'].split('/')[0] for r in ar)=={'original':14,'hard':16,'medium':26}
assert all(r['quality_eligible'] and r['integrity_ok'] and r['quality_status']=='scored' for r in ar)
assert all(r['all_actual_pro_normal'] is True for r in ar)
q=aa['quality']; assert q['full_pass_tasks']+q['partial_credit_tasks']+q['zero_reward_tasks']==56
assert abs(sum(float(r['reward']) for r in ar)-float(q['known_reward_sum']))<1e-5
assert sum(float(r['max_reward']) for r in ar)==q['observed_eligible_max_reward']==114
for g in ['original','hard','medium']:
    rr=[r for r in ar if r['task'].startswith(g+'/')];gg=aa['groups'][g]
    valid=[r for r in rr if r.get('api_comparable') and r.get('api_accuracy') is not None]
    assert gg['api']['eligible_tasks']==len(valid)
    if valid:
        assert gg['api']['passed']==sum(r['api_passed'] for r in valid)
        assert gg['api']['total']==sum(r['api_total'] for r in valid)
        assert close(gg['api']['micro_accuracy'],sum(r['api_passed'] for r in valid)/sum(r['api_total'] for r in valid))
        assert close(gg['api']['macro_accuracy'],statistics.mean(r['api_accuracy'] for r in valid))
    else:
        assert gg['api']['passed'] in (None,0) and gg['api']['total'] in (None,0)
        assert gg['api']['micro_accuracy'] is None and gg['api']['macro_accuracy'] is None
assert sum(r['topology']['subagent_count'] for r in ar)==aa['total_children']
assert sum(r.get('paired_summary_returns',r['delegations']['returned']) for r in ar)==aa['total_summary_returns']
assert sum(bool(r['topology']['parallel_agents_observed']) for r in ar)==aa['tasks_with_parallel_agents']==0
csv_a=read_csv(ROOT/'aorchestra/cells-56.csv')
assert len(csv_a)==56 and {r['task'] for r in csv_a}=={r['task'] for r in ar}
for row in csv_a:
    r=next(r for r in ar if r['task']==row['task'])
    for key in ['reward','e2e_seconds','request_count']:
        assert close(r[key],row[key]),(r['task'],key)
    for key in ['input_tokens','output_tokens','cache_tokens','api_accuracy','focused_accuracy']:
        assert (r.get(key) is None and row[key]=='') or (r.get(key) is not None and close(r[key],row[key])),(r['task'],key)
summ=read_json(ROOT/'harness-dataset-summary-24.json');assert len(summ)==24
assert len({(s['arm'],s['dataset']) for s in summ})==24
assert sum(s['cells'] for s in summ)==448
for s in summ:
    if s['arm']=='aorchestra':
        prefix={'original14':'original','medium26':'medium','mixed16-v4':'hard'}[s['dataset']]
        rr=[r for r in ar if r['task'].startswith(prefix+'/')]
        assert s['cells']==len(rr)
        assert close(s['tokens_input_known'],sum(r['known_settled_usage']['input_tokens'] for r in rr))
        assert close(s['tokens_output_known'],sum(r['known_settled_usage']['output_tokens'] for r in rr))
        assert close(s['e2e_mean_seconds'],statistics.mean(r['e2e_seconds'] for r in rr))
    else:
        src=next(r for r in seven['summary'] if (r['arm'],r['dataset'])==(s['arm'],s['dataset']))
        assert s['cells']==src['certified_cells'] and s['api_passed']==src['api_passed'] and s['api_total']==src['api_total']
for ds,expected in [('medium26',26),('mixed16-v4',16)]:
    matrix=read_csv(ROOT/('api-task-matrix-'+ds+'-eight-arms.csv'));assert len(matrix)==expected
    for row in matrix:
        for arm,value in row.items():
            if arm=='task':continue
            if arm=='aorchestra':r=next(r for r in ar if r['task']==row['task']);v=r['api_accuracy'] if r['api_comparable'] else None
            else:v=next(r for r in seven['baseline_cells'] if r['arm']==arm and r['task']==row['task'])['api_accuracy']
            assert (v is None and value=='') or (v is not None and close(v,value))
pr=read_json(ROOT/'parallel-analysis/native-trigger-evidence.json')['rows'];assert len(pr)==392
assert len(read_csv(ROOT/'parallel-analysis/parallel-trigger-cells-392.csv'))==392
assert read_json(ROOT/'parallel-analysis/checks.json')['source_results_sha256']==sha(ROOT/'seven-harnesses/results.json')
for f in ROOT.rglob('*'):
    if not f.is_file():continue
    assert f.suffix in ['.md','.json','.csv','.py',''] or f.name=='.gitattributes',f.name
    if f.suffix=='.py':continue  # Validators document regex patterns, not credentials.
    text=f.read_text(encoding='utf-8-sig')
    for pat in [r'(?i)(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{16,}',r'gh[pousr]_[A-Za-z0-9]{20,}',r'(?i)Bearer\s+[A-Za-z0-9._-]{12,}',r'(?i)[A-Z]:[\\/]+Users[\\/]',r'/mnt/c/Users/',r'/home/horace/',r'(?i)mlp.ppt24']:
        assert not re.search(pat,text),(f.relative_to(ROOT).as_posix(),pat)
    if f.suffix=='.json':
        x=read_json(f)
        def check_keys(v):
            if isinstance(v,dict):
                assert not (set(v)&{'api_key','authorization_headers','raw_prompt','stdout','stderr','raw_messages','locals'})
                for value in v.values():check_keys(value)
            elif isinstance(v,list):
                for value in v:check_keys(value)
        check_keys(x)
print(json.dumps({'validation':'passed','selected_cells':448,'seven_harness_cells':392,'aorchestra_cells':56,'independent_repeats':4,'summary_groups':24,'api_matrices':'passed','artifact_hashes':'passed','sensitive_material_scan':'passed','provider_requests':0}))
