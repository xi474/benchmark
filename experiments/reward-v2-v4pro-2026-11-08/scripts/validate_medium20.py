"""Independently validate Medium20 selection, unchanged scores and aggregates."""
import collections
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[1]
VIEW=ROOT/'medium20-revision-2026-11-09'
EXCLUDED={f'medium/MP{i:02}' for i in [4,8,9,10,11,24]}
EXPECTED_MEDIUM={f'medium/MP{i:02}' for i in range(1,27)}-EXCLUDED


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def csv_read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def equal(a,b):
    if a is None or b is None:
        assert a is b,(a,b)
    else:
        assert abs(float(a)-float(b))<1e-7,(a,b)


def dsum(rows,key):
    return sum(Decimal(str(r[key])) for r in rows if r.get(key) is not None)


def main():
    data=read(VIEW/'results.json');policy=read(VIEW/'exclusion-policy.json');audit=read(VIEW/'revision-audit.json')
    for name,digest in audit['artifact_sha256'].items():
        assert sha(VIEW/name)==digest,name
    assert audit['build_script_sha256']==sha(ROOT/'scripts/build_medium20.py')
    assert data['exclusion_policy_sha256']==sha(VIEW/'exclusion-policy.json')
    for name,digest in data['source_sha256'].items():
        assert sha(ROOT/name)==digest,name
    assert {r['task'] for r in policy['exclusions']}==EXCLUDED
    assert set(policy['included_medium_tasks'])==EXPECTED_MEDIUM
    assert data['provider_requests']==policy['provider_requests']==0
    assert not policy['scores_modified'] and not policy['task_files_modified'] and not policy['verifier_modified']
    old=read(ROOT/'seven-harnesses/results.json');ao=read(ROOT/'aorchestra/results-56.json')
    source={(r['arm'],r['task']):r for r in old['baseline_cells']}
    source.update({('aorchestra',r['task']):r for r in ao['rows']})
    cache={(r['arm'],r['task']):r for r in read(ROOT/'cache-analysis/results.json')['rows']}
    rows=data['rows'];removed=data['excluded_rows']
    keys={(r['arm'],r['task']) for r in rows};removed_keys={(r['arm'],r['task']) for r in removed}
    assert len(rows)==len(keys)==400 and len(removed)==len(removed_keys)==48
    assert not keys & removed_keys and keys | removed_keys==set(source)
    assert collections.Counter(r['arm'] for r in rows)=={a:50 for a in policy['applies_to_harnesses']}
    assert collections.Counter(r['dataset'] for r in rows)=={'medium20':160,'original14':112,'mixed16-v4':128}
    for arm in policy['applies_to_harnesses']:
        assert {r['task'] for r in rows if r['arm']==arm and r['dataset']=='medium20'}==EXPECTED_MEDIUM
        assert {r['task'] for r in removed if r['arm']==arm}==EXCLUDED
    for r in rows+removed:
        s=source[(r['arm'],r['task'])]
        assert r['analysis_included']==(r['task'] not in EXCLUDED)
        expected_ds={'original':'original14','hard':'mixed16-v4','medium':'medium20'}[r['task'].split('/')[0]]
        if r['task'] in EXCLUDED:expected_ds='medium26-excluded-spec-quality'
        assert r['dataset']==expected_ds
        if r['arm']!='aorchestra':
            for key,value in s.items():
                assert r[key]==(expected_ds if key=='dataset' else value),(r['arm'],r['task'],key)
            expected_quality=s['score_status']=='scored' and not s['api_accuracy_status'].startswith('unscored_')
            assert r['quality_comparable']==expected_quality
        else:
            assert r['native_metrics']==s
            mappings={'trial_id':'trial','classification':'quality_status','certified_reward':'reward',
                      'certified_max_reward':'max_reward','quality_comparable':'quality_eligible',
                      'api_passed':'api_passed','api_total':'api_total','e2e_seconds':'e2e_seconds',
                      'model_requests_sent':'request_count','model_requests_settled':'settled_count',
                      'model_requests_unknown':'unknown_count','tokens_input':'input_tokens',
                      'tokens_output':'output_tokens','tokens_cache_hit_known':'cache_tokens'}
            for target,origin in mappings.items():assert r[target]==s[origin]
            assert r['tokens_input_known']==s['known_settled_usage']['input_tokens']
            assert r['tokens_output_known']==s['known_settled_usage']['output_tokens']
            equal(r['estimated_settled_peak_usd'],s['known_settled_peak_usd'])
            assert r['resource_scope']==ao['resource_scope']
            assert r['observed_subagent_count_reported']==s['topology']['subagent_count']
        for key in ['input_cache_hit_rate','observed_input_cache_hit_rate','cache_rate_status','cache_usage_complete']:
            assert r[key]==cache[(r['arm'],r['task'])][key]
    assert data['latte_independent_repeats']==old['latte_independent_repeats']
    assert len(data['latte_independent_repeats'])==4
    assert len(data['dataset_summary'])==24 and len(data['harness_summary'])==8
    prior_summary=read(ROOT/'harness-dataset-summary-24.json')
    for g in data['dataset_summary']:
        if g['dataset']=='medium20':continue
        prior=next(s for s in prior_summary if (s['arm'],s['dataset'])==(g['arm'],g['dataset']))
        for key in ['cells','api_measured_cells','api_passed','api_total','api_micro_accuracy','api_macro_accuracy',
                    'reward_sum','reward_max_comparable','e2e_mean_seconds','tokens_input_known',
                    'tokens_output_known','tokens_cache_hit_known','unknown_requests','estimated_settled_peak_usd']:
            equal(g[key],prior[key])
    for g in data['dataset_summary']+data['harness_summary']+data['excluded_summary']:
        pool=removed if g['dataset']=='excluded-medium6' else rows
        group=[r for r in pool if r['arm']==g['arm'] and (g['dataset'] in ['all50','excluded-medium6'] or r['dataset']==g['dataset'])]
        assert len(group)==g['cells']
        eligible=[r for r in group if r['quality_comparable']]
        api=[r for r in group if r['api_accuracy'] is not None]
        assert g['quality_comparable_cells']==len(eligible) and g['api_measured_cells']==len(api)
        equal(g['reward_sum'],dsum(eligible,'certified_reward'))
        equal(g['reward_max_comparable'],dsum(eligible,'certified_max_reward'))
        equal(g['registered_max_reward_sum'],dsum(group,'certified_max_reward'))
        assert g['classification_counts']==dict(collections.Counter(r['classification'] for r in group))
        assert g['orchestration_status_counts']==dict(collections.Counter(r['orchestration_status'] if r['orchestration_status'] is not None else 'unknown' for r in group))
        if api:
            assert g['api_passed']==sum(r['api_passed'] for r in api)
            assert g['api_total']==sum(r['api_total'] for r in api)
            equal(g['api_micro_accuracy'],sum(r['api_passed'] for r in api)/sum(r['api_total'] for r in api))
            equal(g['api_macro_accuracy'],statistics.mean(r['api_accuracy'] for r in api))
        else:assert g['api_micro_accuracy'] is None and g['api_macro_accuracy'] is None
        times=[r['e2e_seconds'] for r in group if r['e2e_seconds'] is not None]
        equal(g['e2e_mean_seconds'],statistics.mean(times))
        equal(g['e2e_median_seconds'],statistics.median(times))
        for key in ['tokens_input_known','tokens_output_known','tokens_cache_hit_known','estimated_settled_peak_usd',
                    'model_requests_sent','model_requests_settled']:
            equal(g[key],dsum(group,key))
        assert g['unknown_requests']==sum(r['model_requests_unknown'] for r in group)
        coverage=all(r['cache_rate_status'] in ['observed','not_applicable_zero_input'] for r in group)
        known=dsum(group,'tokens_cache_hit_known')/dsum(group,'tokens_input_known')
        equal(g['observed_input_cache_hit_rate'],known)
        equal(g['input_cache_hit_rate'],known if coverage else None)
        assert g['invoice_usd'] is None
        equal(g['self_check_correlated_loops'],sum(r['self_check_correlated_loops'] for r in group if r.get('self_check_correlated_loops') is not None) if any(r.get('self_check_correlated_loops') is not None for r in group) else None)
    medium=[r for r in rows if r['dataset']=='medium20']
    assert sum(r['score_status']=='invalid_submission' for r in medium)==4
    assert sum(r['classification']=='skipped_pre_send_budget_cap' for r in medium)==1
    assert next(r for r in medium if r['arm']=='codex' and r['task']=='medium/MP14')['classification']=='scored_with_agent_timeout'
    unknown=[r for r in rows if r['model_requests_unknown']]
    assert len(unknown)==1 and unknown[0]['arm']=='roma' and unknown[0]['task']=='original/release_compatibility_program'
    assert unknown[0]['input_cache_hit_rate'] is None
    equal(dsum(rows,'estimated_settled_peak_usd')+dsum(removed,'estimated_settled_peak_usd'),Decimal('185.314606752'))
    for name,key in [('api-task-matrix-medium20-eight-arms.csv','api_accuracy'),
                     ('api-coverage-medium20-eight-arms.csv','api_accuracy_status'),
                     ('input-cache-matrix-medium20-eight-arms.csv','input_cache_hit_rate'),
                     ('cache-coverage-medium20-eight-arms.csv','cache_rate_status')]:
        matrix=csv_read(VIEW/name)
        assert len(matrix)==20 and {r['task'] for r in matrix}==EXPECTED_MEDIUM
        index={(r['arm'],r['task']):r for r in medium}
        for line in matrix:
            assert set(line)=={'task'}|set(policy['applies_to_harnesses'])
            for arm in policy['applies_to_harnesses']:
                value=index[(arm,line['task'])][key]
                if value is None:assert line[arm]==''
                elif isinstance(value,str):assert line[arm]==value
                else:equal(line[arm],value)
    for name,count in [('cells-400.csv',400),('medium20-cells-160.csv',160),('excluded-cells-48.csv',48)]:
        csv_rows=csv_read(VIEW/name);assert len(csv_rows)==count
        index={(r['arm'],r['task']):r for r in rows+removed}
        for r in csv_rows:
            source_row=index[(r['arm'],r['task'])]
            assert r['classification']==source_row['classification'] and r['trial_id']==source_row['trial_id']
            for key in ['certified_reward','certified_max_reward','e2e_seconds','tokens_input_known',
                        'tokens_output_known','tokens_cache_hit_known','estimated_settled_peak_usd','api_accuracy']:
                if source_row[key] is None:assert r[key]==''
                else:equal(r[key],source_row[key])
    for target,origin in [('self-check-loops.csv','seven-harnesses/self-check-loops.csv'),
                          ('parallel-trigger-cells-350.csv','parallel-analysis/parallel-trigger-cells-392.csv')]:
        expected=[r for r in csv_read(ROOT/origin) if r['task'] not in EXCLUDED]
        for r in expected:
            if r['dataset']=='medium26':r['dataset']='medium20'
        assert csv_read(VIEW/target)==expected
    assert len(csv_read(VIEW/'parallel-trigger-cells-350.csv'))==350
    print(json.dumps(dict(validation='passed',current_cells=400,medium20_cells=160,excluded_cells=48,
                          unchanged_source_records=448,summary_groups=24,api_matrices='passed',
                          source_and_artifact_hashes='passed',historical_unknown_preserved=True,provider_requests=0)))


if __name__=='__main__':
    main()
