"""Verify the redacted R7 supplement offline; no credentials or network."""
from pathlib import Path
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime

ROOT = Path(__file__).resolve().parent


def rows(name):
    with (ROOT/name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def same(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-6), (a, b)


def main():
    recorded = {}
    for line in (ROOT/'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert Path(name).name == name and name not in recorded
        recorded[name] = digest
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, name
    assert set(recorded) == {p.name for p in ROOT.iterdir() if p.is_file()} - {'SHA256SUMS'}
    cells = rows('cells.csv')
    assert len(cells) == 3 and {c['task_id'] for c in cells} == {'MP19', 'MP15', 'MP17'}
    assert all(c['scored'] == 'True' and c['monitoring_gate_passed'] == 'True' and c['unknown_usage_requests'] == '0' for c in cells)
    assert all(c['adapter_profile'] == 'responses-chat-normal-v1.0.4' and c['permissions_expanded'] == 'False' for c in cells)
    requests = rows('request_usage.csv')
    assert len({r['request_ref'] for r in requests}) == len(requests)
    req = defaultdict(list)
    offered = defaultdict(list)
    for tool in rows('request_tools.csv'):
        offered[tool['request_ref']].append(tool)
        assert not tool['offered_wire_name'].startswith('bridge_denied_unoffered_')
    fingerprints = defaultdict(list)
    for fingerprint in rows('request_prompt_hashes.csv'):
        assert len(fingerprint['sha256']) == 64
        fingerprints[fingerprint['request_ref']].append(fingerprint)
    for r in requests:
        req[r['trial_id']].append(r)
        assert r['thinking_type'] == 'disabled' and r['response_mode_consistent'] == 'True'
        assert 0 <= float(r['input_cached_tokens']) <= float(r['input_tokens']) and float(r['output_tokens']) >= 0
        assert len(offered[r['request_ref']]) == int(r['actual_tool_count'])
        assert len(fingerprints[r['request_ref']]) == int(r['prompt_fingerprint_count']) > 0
        assert r['actual_tools_status'] == 'observed'
        cost = ((float(r['input_tokens'])-float(r['input_cached_tokens']))*1.32 + float(r['input_cached_tokens'])*.044 + float(r['output_tokens'])*3.96)/1e6
        same(cost, r['estimated_usd'])
    checks = defaultdict(list)
    for c in rows('verifier_checks.csv'):
        checks[c['trial_id']].append(c)
    original_ids = defaultdict(set)
    for r in rows('native_control_api_check_ids.csv'):
        original_ids[r['task_id']].add(r['check_id'])
    agents = rows('agents.csv')
    assert len({(r['trial_id'], r['child_id']) for r in agents}) == len(agents)
    for c in cells:
        identity = c['trial_id']
        api = [r for r in checks[identity] if r['is_api'] == 'True']
        assert {a['check_id'] for a in api} == original_ids[c['task_id']]
        same(len(api), c['api_total'])
        same(sum(a['passed'] == 'True' for a in api), c['api_pass'])
        same(float(c['api_pass'])/float(c['api_total']), c['api_accuracy'])
        same((datetime.fromisoformat(c['harbor_finished_at'])-datetime.fromisoformat(c['harbor_started_at'])).total_seconds(), c['harbor_e2e_sec'])
        for a, b in [('input_tokens','input_tokens'),('output_tokens','output_tokens'),('input_cached_tokens','input_cached_tokens'),('estimated_usd','estimated_usd_known_settled'),('http_duration_sec','model_http_duration_sum_sec')]:
            assert all(r[a] != '' for r in req[identity])
            same(sum(float(r[a]) for r in req[identity]), c[b])
        same(len(req[identity]), c['settled_requests'])
        same(float(c['input_cached_tokens'])/float(c['input_tokens']), c['input_cache_hit_ratio'])
        same(float(c['input_tokens'])+float(c['output_tokens']), c['total_tokens'])
        same(sum(a['trial_id'] == identity for a in agents), c['child_count'])
        known = [r['reasoning_tokens'] for r in req[identity] if r['reasoning_tokens'] != '']
        same(len(known), c['requests_with_reasoning_field'])
        if len(known) < len(req[identity]):
            assert c['reasoning_tokens'] == ''
        else:
            same(sum(float(v) for v in known), c['reasoning_tokens'])
    validation = json.loads((ROOT/'validation.json').read_text())
    assert validation['valid_scored_cells'] == 3 and validation['permissions_expanded'] is False
    ledger = json.loads((ROOT/'batch_ledger.json').read_text())
    assert ledger['sent_count'] == ledger['complete_count'] == len(requests) and ledger['unknown_count'] == 0
    print(json.dumps({'passed': True, 'valid_scored_cells': 3, 'request_records': len(requests), 'child_identities': len(agents),
        'same_api_ids_as_historical_controls': True, 'provider_model_requests': 0}))


if __name__ == '__main__':
    main()
