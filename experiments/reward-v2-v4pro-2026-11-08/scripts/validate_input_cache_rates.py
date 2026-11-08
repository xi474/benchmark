"""Independently verify cache metrics, coverage and matrices against source usage."""
import collections,csv,hashlib,json,pathlib,statistics
from aggregate_input_cache_rates import classify

ROOT=pathlib.Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def close(x,y):return abs(float(x)-float(y))<1e-12
data=read(ROOT/'cache-analysis/results.json');baseline=data['rows'];repeats=data['independent_repeats']
assert len(baseline)==448 and len(repeats)==4
assert len({(r['arm'],r['task']) for r in baseline})==448
assert len({(r['arm'],r['task'],r['trial_id']) for r in baseline+repeats})==452
seven=read(ROOT/'seven-harnesses/results.json');ao=read(ROOT/'aorchestra/results-56.json')
source={(r['arm'],r['task'],'baseline'):r for r in seven['baseline_cells']}
source.update({(r['arm'],r['task'],'independent-repeat'):r for r in seven['latte_independent_repeats']})
source.update({('aorchestra',r['task'],'baseline'):r for r in ao['rows']})
partial=[]
for r in baseline+repeats:
    s=source[r['arm'],r['task'],r['cohort']]
    if r['arm']=='aorchestra':inp=s['known_settled_usage']['input_tokens'];hit=s['cache_tokens'];unknown=s['unknown_count'];complete=hit is not None
    else:inp=s['tokens_input_known'];hit=s['tokens_cache_hit_known'];unknown=s['model_requests_unknown'];complete=s['cache_usage_complete']
    assert r['input_tokens_known']==inp and r['cache_hit_tokens_known']==hit
    assert r['requests_unknown']==unknown and r['cache_usage_complete']==complete
    assert r['cache_miss_tokens_known']==inp-hit and 0<=hit<=inp
    assert close(r['observed_input_cache_hit_rate'],hit/inp)
    assert r['source_sha256']==hashlib.sha256((ROOT/r['source_file']).read_bytes()).hexdigest()
    if unknown or r['requests_sent']!=r['requests_settled']:
        assert r['input_cache_hit_rate'] is None and r['cache_rate_status']=='partial_unknown_request';partial.append((r['arm'],r['task']))
    else:
        assert r['cache_rate_status']=='observed' and close(r['input_cache_hit_rate'],hit/inp)
assert partial==[('roma','original/release_compatibility_program')]
for g in data['harness_summary']+data['dataset_summary']:
    rr=[r for r in baseline if r['arm']==g['arm'] and (g['dataset']=='all56' or r['dataset']==g['dataset'])]
    assert len(rr)==g['cells']
    assert g['input_tokens_known']==sum(r['input_tokens_known'] for r in rr)
    assert g['cache_hit_tokens_known']==sum(r['cache_hit_tokens_known'] for r in rr)
    expected=sum(r['cache_hit_tokens_known'] for r in rr)/sum(r['input_tokens_known'] for r in rr)
    assert close(expected,g['observed_input_cache_hit_rate'])
    valid=[r for r in rr if r['cache_rate_status']=='observed'];assert g['cache_measured_cells']==len(valid)
    assert close(g['input_cache_hit_rate_macro'],statistics.mean(r['input_cache_hit_rate'] for r in valid))
    if len(valid)==len(rr):assert close(g['input_cache_hit_rate'],expected)
    else:assert g['input_cache_hit_rate'] is None
for ds,n in [('original14',14),('mixed16-v4',16),('medium26',26)]:
    matrix=rows(ROOT/f'cache-analysis/matrix-{ds}.csv');coverage=rows(ROOT/f'cache-analysis/matrix-coverage-{ds}.csv')
    assert len(matrix)==len(coverage)==n
    assert len(matrix[0])==9
    for m,c in zip(matrix,coverage):
        assert m['task']==c['task']
        for arm in m.keys()-{'task'}:
            r=next(r for r in baseline if r['arm']==arm and r['task']==m['task'])
            assert c[arm]==r['cache_rate_status']
            assert (r['input_cache_hit_rate'] is None and m[arm]=='') or (r['input_cache_hit_rate'] is not None and close(m[arm],r['input_cache_hit_rate']))
long=rows(ROOT/'cache-analysis/cells-448.csv');assert len(long)==448
for r in long:
    src=next(s for s in baseline if (s['arm'],s['task'])==(r['arm'],r['task']))
    assert int(r['input_tokens_known'])==src['input_tokens_known'] and int(r['cache_hit_tokens_known'])==src['cache_hit_tokens_known']
    assert r['cache_rate_status']==src['cache_rate_status']
    assert (r['input_cache_hit_rate']=='' and src['input_cache_hit_rate'] is None) or close(r['input_cache_hit_rate'],src['input_cache_hit_rate'])
summary=read(ROOT/'harness-dataset-summary-24.json')
for s in summary:
    g=next(g for g in data['dataset_summary'] if (g['arm'],g['dataset'])==(s['arm'],s['dataset']))
    assert all(s[k]==g[k] for k in ['input_cache_hit_rate','observed_input_cache_hit_rate','input_cache_hit_rate_macro','cache_rate_status','cache_measured_cells','cache_partial_cells','cache_missing_cells'])
# Semantic guards: a real zero is measurable; missing, partial and zero denominator are not zero.
assert classify(10,0,True,1,1,0)==(0.0,0.0,'observed')
assert classify(10,None,False,1,1,0)==(None,None,'unavailable_cache_or_input')
assert classify(10,5,True,2,1,1)==(None,0.5,'partial_unknown_request')
assert classify(0,0,True,0,0,0)==(None,None,'not_applicable_zero_input')
assert classify(10,5,True,None,None,None)==(None,0.5,'unknown_request_coverage')
try:classify(10,11,True,1,1,0)
except ValueError:pass
else:raise AssertionError('Cache over input must be rejected')
assert (9+0)/(10+90)!=statistics.mean([9/10,0/90]),'Micro and macro must remain different'
print(json.dumps({'cache_validation':'passed','baseline_cells':448,'complete_rates':447,'partial_rates':1,'independent_repeats':4,'dataset_matrices':3,'coverage_matrices':3,'unknown_vs_zero_guards':'passed','provider_requests':0}))
