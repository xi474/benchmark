"""Verify the public accuracy-regression annex offline, without API calls."""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import math
import re

ROOT=Path(__file__).resolve().parent

def rows(name):
    with (ROOT/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def same(a,b):
    assert math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-6),(a,b)

def main():
    checksums={}
    for line in (ROOT/'SHA256SUMS').read_text(encoding='utf8').splitlines():
        sha,name=line.split('  ',1)
        assert Path(name).name==name and name not in checksums
        checksums[name]=sha
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    assert set(checksums)=={p.name for p in ROOT.iterdir() if p.is_file()}-{'SHA256SUMS'}
    pairs=rows('paired-check-census.csv');transitions=rows('check-transitions.csv')
    assert len(pairs)==104 and len(transitions)==2592
    key=lambda r:(r['harness'],r['dataset'],r['task_id'])
    assert len({key(r) for r in pairs})==104
    assert len({(*key(r),r['check_id']) for r in transitions})==2592
    grouped=defaultdict(list)
    for c in transitions:
        assert 'explicit_detail' not in c and 'native_detail' not in c
        assert c['native_passed'] in ['True','False'] and c['explicit_passed'] in ['True','False']
        a,b=c['explicit_passed']=='True',c['native_passed']=='True'
        expected='regression' if b and not a else 'improvement' if a and not b else 'both-pass' if a else 'both-fail'
        assert c['transition']==expected
        grouped[key(c)].append(c)
    source={}
    for fn in ['../explicit-medium20-core6-four-harness-v4pro-20261112/completed_cells.csv',
               '../explicit-medium20-codex3-chat-normal-r7-20261113/cells.csv']:
        for r in rows(fn):
            assert r['trial_id'] not in source
            source[r['trial_id']]=r
    assert len(source)==208
    provenance=rows('provenance.csv');assert len(provenance)==208
    for r in provenance:
        original=source[r['trial_id']]
        assert r['result_sha256']==original['result_sha256']
        assert r['score_sha256']==original['score_sha256']
        assert r['source_result_ref']==original['source_result_ref']
        assert r['source_score_ref']==original['source_score_ref']
        assert not r['source_result_ref'].startswith(('/', '\\'))
        assert not r['source_score_ref'].startswith(('/', '\\'))
        assert r['mode_status']==original['mode_status']
    for p in pairs:
        cs=grouped[key(p)]
        assert len(cs)==int(p['api_total'])
        assert int(p['native_api'])==sum(c['native_passed']=='True' for c in cs)
        assert int(p['explicit_api'])==sum(c['explicit_passed']=='True' for c in cs)
        assert int(p['regressed_checks'])==sum(c['transition']=='regression' for c in cs)
        assert int(p['improved_checks'])==sum(c['transition']=='improvement' for c in cs)
        assert int(p['delta'])==int(p['explicit_api'])-int(p['native_api'])
        assert int(p['delta'])==int(p['improved_checks'])-int(p['regressed_checks'])
        for arm in ['explicit','native']:
            r=source[p[arm+'_trial']]
            same(p[arm+'_api'],r['api_pass']);same(p['api_total'],r['api_total'])
            same(p[arm+'_e2e'],r['harbor_e2e_sec']);same(p[arm+'_tokens'],r['total_tokens'])
        same(p['children'],source[p['explicit_trial']]['child_count'])
    summaries=rows('stratified-summary.csv')
    for s in summaries:
        group=[p for p in pairs if p['harness']==s['harness'] and (s['dataset']=='all26' or p['dataset']==s['dataset'])]
        predicates={'all-selected':lambda p:True,
                    'exclude-budget-timeout-pairs':lambda p:p['either_budget_or_timeout']=='False',
                    'observed-child-created':lambda p:int(p['children'])>0,
                    'explicit-output-cap':lambda p:'cap' in p['explicit_terminal']}
        selected=[p for p in group if predicates[s['selection']](p)]
        assert len(selected)==int(s['tasks'])
        for source_key,target in [('native_api','native_api'),('explicit_api','explicit_api'),('api_total','api_total'),('regressed_checks','regressed_checks'),('improved_checks','improved_checks')]:
            same(sum(int(p[source_key]) for p in selected),s[target])
        total=int(s['api_total']);n=int(s['native_api']);e=int(s['explicit_api'])
        same(n/total,s['native_accuracy']);same(e/total,s['explicit_accuracy']);same((e-n)/total*100,s['delta_pp'])
        same(sum(int(p['explicit_tokens']) for p in selected)/len(selected),s['explicit_mean_tokens'])
        same(sum(int(p['native_tokens']) for p in selected)/len(selected),s['native_mean_tokens'])
    codex=[p for p in pairs if p['harness']=='codex' and p['dataset']=='medium20-original']
    caps=[p for p in codex if 'cap' in p['explicit_terminal']]
    assert {p['task_id'] for p in caps}=={'MP20','MP22'}
    assert sum(int(p['delta']) for p in caps)==-58
    assert sum(int(p['delta']) for p in codex if p not in caps)==0
    r7=[p for p in codex if p['adapter_stratum']=='r7-repaired-chat-disabled']
    assert {p['task_id'] for p in r7}=={'MP15','MP17','MP19'}
    assert sum(int(p['explicit_api']) for p in r7)==58 and sum(int(p['api_total']) for p in r7)==70
    assert all(int(p['regressed_checks'])==int(p['improved_checks'])==0 for p in r7)
    original=[p for p in codex if p['adapter_stratum']=='original' and p not in caps]
    assert len(original)==15 and sum(int(p['explicit_api']) for p in original)==331
    assert sum(int(p['native_api']) for p in original)==331 and sum(int(p['api_total']) for p in original)==376
    with (ROOT/'codex-cap-request-evidence.json').open(encoding='utf8') as f:cap_requests=json.load(f)
    request_source={r['request_ref']:r for r in rows('../explicit-medium20-core6-four-harness-v4pro-20261112/request_usage.csv')}
    assert len(cap_requests)==2
    for r in cap_requests:
        assert request_source[r['request_ref']]==r
        assert int(r['output_tokens'])==32768
        assert int(r['reasoning_tokens'])==({'MP20':30142,'MP22':32768}[r['task_id']])
    attestation=json.loads((ROOT/'task-file-comparison.json').read_text(encoding='utf8'))
    assert len(attestation)==20 and sum(r['checked'] for r in attestation)==1573
    assert not any(r['different'] or r['missing'] for r in attestation)
    evidence=json.loads((ROOT/'trace-evidence-index.json').read_text(encoding='utf8'))
    assert len(evidence['cases'])==9
    for case in evidence['cases']:
        assert set(case['arms'])=={'native','explicit'}
        for arm,record in case['arms'].items():
            assert record['source_ref'] and not record['source_ref'].startswith(('/', '\\'))
            assert re.fullmatch(r'[0-9a-f]{64}',record['source_sha256'])
            assert record['event_count']==len(record['events'])
    # Links in the report resolve in the repository; no local personal paths are published.
    report=(ROOT/'README.md').read_text(encoding='utf8')
    for target in re.findall(r'\]\(([^)]+)\)',report):
        if not target.startswith(('http://','https://','#')):assert (ROOT/target.split('#')[0]).exists(),target
    for p in ROOT.iterdir():
        if p.is_file():
            text=p.read_text(encoding='utf-8-sig')
            assert not re.search(r'[A-Za-z]:[/\\](?:Users|home)[/\\]|/home/[a-z_][a-z0-9_-]*/|/mnt/[a-z]/Users/',text),p.name
            assert not re.search(r'(?<![A-Za-z0-9_-])sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}',text),p.name
            assert not re.search(r'(?<![A-Za-z0-9_-])gh[pousr]_[A-Za-z0-9]{30,}',text),p.name
            assert not re.search(r'(?<![A-Za-z0-9_-])github_pat_[A-Za-z0-9_]{30,}',text),p.name
            assert ('PRIVATE'+' KEY'+'-----') not in text,p.name
    print(json.dumps({'status':'passed','pairs':104,'selected_scored_rows':208,'paired_api_checks':2592,
        'codex_cap_net_loss':58,'r7_check_outcomes_equal_to_native':True,
        'task_snapshot_comparison':'local-attestation-1573-matching-files',
        'privacy':'redacted-package-only','provider_model_requests':0},ensure_ascii=False))

if __name__=='__main__':main()
