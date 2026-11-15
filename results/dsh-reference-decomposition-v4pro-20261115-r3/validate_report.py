"""Validate the public report package offline; never runs an agent or verifier."""
from pathlib import Path
import json,hashlib,statistics,math
ROOT=Path(__file__).resolve().parent
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
def equal(a,b):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-7),(a,b)
def validate():
    cells=read('cells.json');summary=read('summary.json');checks=read('api-checks.json');pairs=read('paired-comparison.json');trace=read('trace-summary.json')
    assert len(cells)==len({c['trial_id'] for c in cells})==12
    assert len(pairs)==6 and len(checks)==144
    assert sum(c['passed'] is not None for c in checks)==132
    for c in cells:
        equal(c['total_tokens'],c['input_tokens']+c['output_tokens'])
        equal(c['e2e_sec'],c['agent_sec']+c['verifier_queue_sec']+c['verifier_held_sec']+c['other_sec'])
        observed=[x for x in checks if x['trial_id']==c['trial_id'] and x['passed'] is not None]
        if c['api_total'] is None:assert not observed and c['exception']=='VerifierTimeoutError'
        else:assert len(observed)==c['api_total']==12 and sum(x['passed'] for x in observed)==c['api_pass']
        assert c['protocol_issued']==c['protocol_matched']
    groups=summary['groups'];cohorts=summary['cohorts']
    sets={'all':pairs,'both_scored':[p for p in pairs if p['both_scored']],'both_research_complete_and_scored':[p for p in pairs if p['both_scored'] and p['both_research_complete']]}
    assert [len(sets[k]) for k in sets]==[6,5,4]
    for name,selected in sets.items():
        g=groups if name=='all' else cohorts[name]
        for arm,key in [('single','single_trial_id'),('guided','multi_trial_id')]:
            ids={p[key] for p in selected};cs=[x for x in cells if x['trial_id'] in ids];v=g[arm]
            assert len(cs)==v['n'] and sum(x['api_total'] is not None for x in cs)==v['scored']
            for field in ['input_tokens','output_tokens','total_tokens','estimated_usd']:
                equal(sum(x[field] for x in cs),v[field])
            equal(sum(x['api_pass'] or 0 for x in cs),v['api_pass']);equal(sum(x['api_total'] or 0 for x in cs),v['api_total'])
            equal(statistics.mean(x['e2e_sec'] for x in cs),v['mean_e2e_sec'])
            equal(statistics.mean(x['agent_sec'] for x in cs),v['mean_agent_sec'])
    assert sum(x['protocol_matched'] for x in cells)==105
    assert sum(x['requests'] for x in cells)==summary['ledger']['complete_count']==788
    equal(sum(x['estimated_usd'] for x in cells),summary['ledger']['settled_peak_usd'])
    assert sum(len(x['children']) for x in cells)==trace['child_count']==6
    assert sum(c['model_responses'] for x in cells for c in x['children'])==trace['child_model_responses']==187
    assert sum(c['completed_tools'] for x in cells for c in x['children'])==trace['completed_child_dispatches']==197
    assert sum(x['parent_receipt_count'] for x in cells)==trace['parent_receipt_records']==13
    hashes=read('SHA256SUMS.json');files={str(p.relative_to(ROOT)).replace('\\','/') for p in ROOT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.json' and '__pycache__' not in p.parts}
    assert set(hashes)==files
    for name,h in hashes.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
    return dict(passed=True,trials=12,pairs=6,observed_api_checks=132,unknown_api_check_slots=12,settled_requests=788,hashed_files=len(hashes),model_requests=0)
if __name__=='__main__':print(json.dumps(validate(),ensure_ascii=False))
