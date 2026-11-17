"""Recalculate bundled secondary metrics offline, with no outside data paths."""
from pathlib import Path
import hashlib
import json
import math
import statistics

P=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def compute(data):
    rows=data['all_attempts'];by={x['trial_id']:x for x in rows}
    assert len(by)==len(rows)==153
    ids=data['reporting_scope']['reporting_trial_ids']
    assert len(ids)==len(set(ids))==145 and set(ids)<=set(by)
    excluded=set(data['reporting_scope']['excluded_mabench_trial_ids'])
    assert len(excluded)==8 and not excluded.intersection(ids) and set(ids)|excluded==set(by)
    results={};selected=set()
    for key,cohort in data['cohorts'].items():
        if not cohort.get('display'):continue
        groups={}
        for arm,expected in cohort['groups'].items():
            own=[by[i] for i in expected['trial_ids']];selected.update(expected['trial_ids'])
            assert len({x['trial_id'] for x in own})==len(own) and all(x['arm']==arm for x in own)
            valid=[x for x in own if x['functional_total'] is not None]
            inp=sum(x['known_input_tokens'] for x in own);out=sum(x['known_output_tokens'] for x in own)
            caches=[x['cache_tokens'] for x in own]
            cached=sum(caches) if all(x is not None for x in caches) else None
            mean=lambda name:statistics.mean(x[name] for x in own if x[name] is not None)
            numerator=sum(x['functional_passed'] for x in valid) if valid else None
            denominator=sum(x['functional_total'] for x in valid) if valid else None
            observed=dict(n=len(own),scored=sum(x['success'] is not None for x in own),
                successes=sum(x['success'] is True for x in own),functional_passed=numerator,functional_total=denominator,
                functional_micro=numerator/denominator if denominator else None,
                functional_macro=statistics.mean(x['functional_passed']/x['functional_total'] for x in valid) if valid else None,
                input_tokens=inp,output_tokens=out,total_tokens=inp+out,cache_tokens=cached,
                cache_hit_rate=cached/inp if cached is not None and inp else None,
                estimated_peak_usd=sum(x['estimated_peak_usd'] for x in own),
                child_triggered_trials=sum(bool(x['children']) for x in own),children=sum(x['children'] or 0 for x in own),
                usage_complete=all(x['usage_complete'] for x in own),normal=sum(x['uninterrupted'] is True for x in own),
                e2e_mean_sec=None if cohort.get('quality_only') else mean('e2e_sec'),
                agent_mean_sec=None if cohort.get('quality_only') else mean('agent_sec'),
                tokens_mean=None if cohort.get('quality_only') else (inp+out)/len(own),
                cost_mean_usd=None if cohort.get('quality_only') else sum(x['estimated_peak_usd'] for x in own)/len(own))
            for name,value in observed.items():
                wanted=expected.get(name)
                if isinstance(value,float):assert math.isclose(value,wanted,rel_tol=1e-10,abs_tol=1e-8),(key,arm,name,value,wanted)
                else:assert value==wanted,(key,arm,name,value,wanted)
            groups[arm]=observed
        results[key]=dict(label=cohort['label'],quality_only=cohort.get('quality_only'),groups=groups)
    assert len(selected)==130
    assert results['mabench_optional']['groups']['M']['children']==0
    assert results['complex_final30']['groups']['M']['child_triggered_trials']==30
    ledgers={}
    for key,own in [('all153',rows),('main145',[by[i] for i in ids])]:
        ledgers[key]=dict(attempts=len(own),sent=sum(x['requests_sent'] for x in own),settled=sum(x['requests_settled'] for x in own),
            unknown=sum(x['requests_unknown'] for x in own),known_peak_estimated_usd=sum(x['estimated_peak_usd'] for x in own))
    assert (ledgers['all153']['sent'],ledgers['all153']['settled'],ledgers['all153']['unknown'])==(7743,7741,2)
    assert (ledgers['main145']['sent'],ledgers['main145']['settled'],ledgers['main145']['unknown'])==(7639,7637,2)
    assert math.isclose(ledgers['all153']['known_peak_estimated_usd'],53.875767528,abs_tol=1e-9)
    for row in rows:
        if row['usage_complete'] and row['cache_tokens'] is not None:
            cost=((row['known_input_tokens']-row['cache_tokens'])*1.32+row['cache_tokens']*.044+row['known_output_tokens']*3.96)/1000000
            assert math.isclose(cost,row['estimated_peak_usd'],abs_tol=1e-8),row['trial_id']
    condition_sources=read(P/'evidence/condition-source-registry.json')
    for source in condition_sources['sources']:
        for prompt in source['prompts']:
            path=(P/prompt['bundled_path']).resolve();assert P.resolve() in path.parents
            assert hashlib.sha256(path.read_bytes()).hexdigest()==prompt['sha256']
    return dict(passed=True,selected_unique_attempts=130,main_operational_attempts=145,all_operational_attempts=153,
        ledgers=ledgers,cohorts=results,source_paths_read=False,network_requests=0,model_requests=0,
        limitation='Recalculates bundled secondary metrics/prompt hashes, not full unbundled native traces or original scoring replay.')

if __name__=='__main__':
    result=compute(read(P/'comparison.json'))
    (P/'portable-recalculation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['ledgers','cohorts']},ensure_ascii=False))
