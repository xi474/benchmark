"""Offline aggregation only: never starts a trial, calls a provider, or edits sources."""
from __future__ import annotations
import collections
import csv
import hashlib
import importlib.util
import json
import math
import statistics
import sys
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

WORKSPACE = Path('local-artifacts://project')
OUT = WORKSPACE / 'outputs/qwen59-final-report-20261126-v1'
SELECTION = WORKSPACE / 'outputs/qwen-latte-workspace-audit-20261126/corrected-matrix-selection.json'
ROOT = Path('local-artifacts://wsl-runs')
BATCHES = {
    'original': 'upstream59-v21-qwen38-max-off-20261126-r1',
    'opencode_git_repair': 'qwen59-opencode-git-20261126-r2',
    'latte_workspace_repair': 'qwen59-latte-v21-20261126-r2',
    'latte_ms02_rate_limit_retry': 'qwen59-latte-ms02-20261126-r3',
    'latte_remaining_two_rate_limit_retry': 'qwen59-latte-two-20261126-r4',
}
ORDER = ['codex', 'dsh', 'opencode', 'langgraph', 'latte-planning-adapted', 'nanobot']
LABEL = dict(zip(ORDER, ['Codex', 'DSH', 'OpenCode', 'LangGraph', 'LATTE 适配版', 'Nanobot']))
spec = importlib.util.spec_from_file_location('workspace_reward', WORKSPACE / 'scoring/workspace_reward.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def dump(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def csv_out(name, rows):
    if not rows:
        return
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def dt(v):
    return datetime.fromisoformat(v.replace('Z', '+00:00')) if v else None

def seconds(start, finish):
    return (dt(finish) - dt(start)).total_seconds() if start and finish else None

def percentile(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    idx = (len(xs) - 1) * p
    lo, hi = math.floor(idx), math.ceil(idx)
    return xs[lo] * (hi - idx) + xs[hi] * (idx - lo) if lo != hi else xs[lo]

def group(task):
    return 'MS10' if task.startswith('MS') else 'MP25' if task.startswith('MP') else 'C20' if task.startswith('C') else 'N4'

def close(a, b, eps=1e-6):
    if abs(float(a) - float(b)) > eps:
        raise AssertionError((a, b))

def tokenize(events):
    return {
        'input_tokens': sum(x['usage']['input_tokens'] for x in events),
        'output_tokens': sum(x['usage']['output_tokens'] for x in events),
        'cache_tokens': sum(x['usage'].get('cache_tokens', 0) or 0 for x in events),
        'cache_usage_observed_requests': sum(x['usage'].get('cache_observed') is True for x in events),
        'list_cost_cny': float(sum((Decimal(str(x['cost_cny_upper_bound'])) for x in events), Decimal(0))),
    }

def terminal_label(o, result, events, resource_dir):
    if o['harness'] == 'latte-planning-adapted':
        f = resource_dir / 'latte-events.jsonl'
        native = [json.loads(line) for line in f.read_text().splitlines() if line.strip()] if f.exists() else []
        ends = [e for e in native if e.get('type') == 'planning_phase_end']
        if ends and ends[-1].get('tasks_discovered') == 0:
            return 'planning_empty_5_turns'
        if o.get('terminal_classification') == 'native_round_limit_incomplete':
            return 'native_round_limit_100'
        if o.get('terminal'):
            msg = (result.get('exception_info') or {}).get('exception_message', '')
            if 'max_rounds' in msg and any(e.get('type') == 'run_end' for e in native):
                return 'native_run_incomplete'
            return o.get('terminal_classification') or 'other_native_nonzero'
        return 'normal_agent_exit'
    if not o.get('terminal'):
        return 'normal_agent_exit'
    used = sum(e['usage']['input_tokens'] + e['usage']['output_tokens'] for e in events)
    if used >= 2_000_000:
        return 'observed_cumulative_token_cap_2M'
    msg = (result.get('exception_info') or {}).get('exception_message', '')
    if o['harness'] == 'nanobot' and o['task_id'] == 'C058' and '190' in msg:
        return 'native_context_limit'
    return o.get('terminal') or 'other_nonzero'

def make_row(o, source, *, selected=False):
    tid = o['trial_id']
    events = SETTLED.get(tid, [])
    sent = SENT.get(tid, set())
    unknown = UNKNOWN.get(tid, set())
    if selected:
        assert len(sent) == len(events) == o['requests_sent'] == o['requests_settled']
        assert not unknown and o['requests_unknown'] == 0
        for k in ['technical_passed', 'actual_mode_verified', 'request_tools_and_prompt_observed', 'resources_observed']:
            assert o.get(k) is True, (tid, k)
    score = o.get('score') or {}
    result_path = o.get('result_file')
    result = read(result_path) if result_path and Path(result_path).is_file() else {}
    segment = SEGMENTS[source]
    score_file = segment / 'offline-scores' / (tid + '.json')
    score_hash_verified = False
    if score:
        if score_file.is_file():
            receipt = read(score_file)
            assert receipt.get('score', receipt) == score, ('score content mismatch', tid)
            if receipt.get('original_result_sha256'):
                assert sha(result_path) == receipt['original_result_sha256'], ('original result hash', tid)
            if o.get('score_sha256'):
                assert sha(score_file) == o['score_sha256']
            score_hash_verified = True
        if selected:
            assert score_hash_verified
        reward = policy.task_reward(difficulty=score['reward_difficulty'], passed=score['passed_verifiers'], total=score['total_verifiers'], strict_pass=score['strict_pass'], integrity_ok=score['integrity_ok'])
        assert reward is not None and reward == Decimal(str(score['reward']))
        frozen = FROZEN[o['task_id']]
        assert score['total_verifiers'] == len(frozen['units'])
        assert score['core_transform_cases_total'] == sum(u['group'] == 'A' for u in frozen['units'])
        assert score['reward_difficulty'] == frozen['reward_difficulty']
        assert len(score['checks']) == score['total_verifiers']
        assert sum(c['passed'] for c in score['checks']) == score['passed_verifiers']
    else:
        reward = None
    usage = tokenize(events)
    if o.get('estimated_list_cost_cny') is not None:
        close(usage['list_cost_cny'], o['estimated_list_cost_cny'])
    agent = Path(result_path).parent / 'agent' if result_path else None
    samples = []
    if agent and (agent / 'native-resources.csv').exists():
        with (agent / 'native-resources.csv').open() as f:
            samples = list(csv.DictReader(f))
    if selected:
        assert samples, ('no actual resource samples', tid)
    child = (o.get('native') or {}).get('child_count')
    row = {
        'harness': o['harness'], 'harness_display': LABEL[o['harness']], 'task_id': o['task_id'],
        'task_group': group(o['task_id']), 'stage': o.get('stage'), 'trial_id': tid,
        'selected_source': source, 'selected_for_matrix': selected,
        'model': 'qwen3.8-max', 'enable_thinking': False,
        'release': 'v2.1.0', 'raw_score_benchmark_version': score.get('benchmark_version'),
        'reward_policy': policy.SCORING_REVISION, 'reward_difficulty': score.get('reward_difficulty'),
        'empirical_difficulty': score.get('empirical_difficulty'), 'max_reward': o.get('max_reward'),
        'score_status': score.get('status'), 'integrity_ok': score.get('integrity_ok'),
        'public_pass': score.get('public_pass'), 'strict_pass': score.get('strict_pass'),
        'api_passed': score.get('core_transform_cases_passed'), 'api_total': score.get('core_transform_cases_total'),
        'api_rate': score.get('core_transform_case_pass_rate'),
        'registered_passed': score.get('passed_verifiers'), 'registered_total': score.get('total_verifiers'),
        'reward': str(reward) if reward is not None else None,
        'normalized_reward': float(reward / Decimal(o['max_reward'])) if reward is not None else None,
        'e2e_seconds': seconds(result.get('started_at'), result.get('finished_at')),
        'agent_seconds': seconds((result.get('agent_execution') or {}).get('started_at'), (result.get('agent_execution') or {}).get('finished_at')),
        'verifier_seconds': seconds((result.get('verifier') or {}).get('started_at'), (result.get('verifier') or {}).get('finished_at')),
        'environment_setup_seconds': seconds((result.get('environment_setup') or {}).get('started_at'), (result.get('environment_setup') or {}).get('finished_at')),
        'agent_setup_seconds': seconds((result.get('agent_setup') or {}).get('started_at'), (result.get('agent_setup') or {}).get('finished_at')),
        'started_at_utc': result.get('started_at'), 'finished_at_utc': result.get('finished_at'),
        'requests_sent': len(sent), 'requests_settled': len(events), 'requests_unknown': len(unknown),
        **usage,
        'total_tokens': usage['input_tokens'] + usage['output_tokens'],
        'input_cache_hit_rate': usage['cache_tokens'] / usage['input_tokens'] if usage['input_tokens'] else None,
        'actual_billed_cost_cny': None, 'fee_is_invoice': False,
        'native_child_count': child,
        'resource_sample_count': len(samples),
        'sampled_peak_memory_mib': max((float(x['memory_current_bytes']) / 2**20 for x in samples if x.get('memory_current_bytes')), default=None),
        'raw_agent_exception': o.get('terminal'),
        'terminal_classification': terminal_label(o, result, events, agent) if result else 'zero_send_quarantine',
        'technical_evidence_passed': o.get('technical_passed'),
        'actual_mode_verified': o.get('actual_mode_verified'),
        'score_hash_verified': score_hash_verified,
        'score_sha256': o.get('score_sha256'),
        'instruction_sha256': o.get('instruction_sha256'), 'registry_sha256': o.get('registry_sha256'),
        'result_file': result_path, 'score_file': str(score_file) if score_file.exists() else None,
    }
    if row['e2e_seconds'] is not None:
        assert row['e2e_seconds'] >= 0
    if selected:
        assert row['e2e_seconds'] is not None
    return row

def aggregate(rows, name):
    n = len(rows)
    scoring = [r for r in rows if r['reward'] is not None]
    api = [r for r in scoring if r['api_total']]
    passed, total = sum(r['api_passed'] for r in api), sum(r['api_total'] for r in api)
    reward = sum((Decimal(r['reward']) for r in scoring), Decimal(0))
    max_reward = sum(r['max_reward'] for r in rows)
    ti, to, tc = (sum(r[k] for r in rows) for k in ['input_tokens', 'output_tokens', 'cache_tokens'])
    times = [r['e2e_seconds'] for r in rows if r['e2e_seconds'] is not None]
    child_known = [r for r in rows if r['native_child_count'] is not None]
    res = {
        'group': name, 'trials': n, 'scored_trials': len(scoring), 'strict_passed': sum(r['strict_pass'] is True for r in rows),
        'strict_acc': sum(r['strict_pass'] is True for r in rows) / n,
        'api_passed': passed, 'api_total': total, 'api_micro_acc': passed / total if total else None,
        'api_macro_acc': statistics.mean(r['api_passed'] / r['api_total'] for r in api) if api else None,
        'registered_passed': sum(r['registered_passed'] for r in scoring),
        'registered_total': sum(r['registered_total'] for r in scoring),
        'reward_sum': str(reward), 'max_reward_sum': max_reward,
        'reward_weighted_rate': float(reward / Decimal(max_reward)),
        'reward_task_macro_rate': statistics.mean(r['normalized_reward'] for r in scoring),
        'e2e_observed_trials': len(times), 'mean_e2e_seconds': statistics.mean(times) if times else None,
        'median_e2e_seconds': statistics.median(times) if times else None, 'p95_e2e_seconds': percentile(times, .95),
        'sum_e2e_seconds': sum(times),
        'mean_agent_seconds': statistics.mean(r['agent_seconds'] for r in rows if r['agent_seconds'] is not None),
        'mean_verifier_seconds': statistics.mean(r['verifier_seconds'] for r in rows if r['verifier_seconds'] is not None),
        'input_tokens': ti, 'output_tokens': to, 'total_tokens': ti + to, 'cache_tokens': tc,
        'input_cache_hit_rate': tc / ti if ti else None,
        'list_cost_cny': float(sum((Decimal(str(r['list_cost_cny'])) for r in rows), Decimal(0))),
        'mean_list_cost_cny': sum(r['list_cost_cny'] for r in rows) / n,
        'actual_billed_cost_cny': None, 'fee_is_invoice': False,
        'requests_sent': sum(r['requests_sent'] for r in rows), 'requests_settled': sum(r['requests_settled'] for r in rows),
        'requests_unknown': sum(r['requests_unknown'] for r in rows),
        'nonzero_agent_trials': sum(bool(r['raw_agent_exception']) for r in rows),
        'integrity_failed_trials': sum(r['integrity_ok'] is False for r in rows),
        'technical_evidence_passed': sum(r['technical_evidence_passed'] is True for r in rows),
        'children_observation_known_trials': len(child_known),
        'observed_trials_with_children': sum(r['native_child_count'] > 0 for r in child_known),
        'observed_child_id_count': sum(r['native_child_count'] for r in child_known),
        'all_trials_have_native_child_count': len(child_known) == n,
    }
    return res

def main():
    global SEGMENTS, SETTLED, SENT, UNKNOWN, FROZEN
    OUT.mkdir(exist_ok=True)
    selection = read(SELECTION)
    manifest = read(ROOT / BATCHES['original'] / 'manifest.json')
    assert selection['selected_logical_cells'] == 354
    assert manifest['enable_thinking'] is False
    assert manifest['price_cny_per_million'] == {'input_without_cache_discount': 12, 'output': 36}, manifest['price_cny_per_million']
    FROZEN = {}
    source_proofs = []
    for c in manifest['cells']:
        task = ROOT / BATCHES['original'] / 'tasks' / c['task_id']
        assert sha(task / 'instruction.md') == c['instruction_sha256']
        assert sha(task / 'tests/release-registry.json') == c['registry_sha256']
        FROZEN[c['task_id']] = read(task / 'tests/release-registry.json')
    SEGMENTS, SETTLED, SENT, UNKNOWN = {}, collections.defaultdict(list), collections.defaultdict(set), collections.defaultdict(set)
    all_events, batch_rows, history = {}, [], []
    for source, name in BATCHES.items():
        root = ROOT / name
        segment = root / 'runs/segment-01'
        SEGMENTS[source] = segment
        ledger = read(segment / 'gateway-ledger.json')
        outs = read(segment / 'paid-outcomes.json')
        source_proofs += [{'file': str(root / 'manifest.json'), 'sha256': sha(root / 'manifest.json')}, {'file': str(segment / 'gateway-ledger.json'), 'sha256': sha(segment / 'gateway-ledger.json')}, {'file': str(segment / 'gateway-requests.jsonl'), 'sha256': sha(segment / 'gateway-requests.jsonl')}, {'file': str(segment / 'paid-outcomes.json'), 'sha256': sha(segment / 'paid-outcomes.json')}]
        local_settled, local_sent, local_unknown = {}, set(), set()
        for line in (segment / 'gateway-requests.jsonl').open():
            if not line.strip():
                continue
            e = json.loads(line)
            rid, typ, tid = e.get('request_id'), e.get('type'), e.get('trial_id')
            if typ == 'sent':
                SENT[tid].add(rid)
                local_sent.add(rid)
            elif typ == 'settled':
                if rid in all_events:
                    assert all_events[rid] == e
                    continue
                all_events[rid] = e
                local_settled[rid] = e
                SETTLED[tid].append(e)
                assert e['model'] == 'qwen3.8-max' and e['enable_thinking'] is False
                assert e['usage']['cache_observed'] is True
                assert 0 <= e['usage']['cache_tokens'] <= e['usage']['input_tokens']
                close(e['cost_cny_upper_bound'], (e['usage']['input_tokens'] * 12 + e['usage']['output_tokens'] * 36) / 1e6)
            elif typ == 'unknown':
                UNKNOWN[tid].add(rid)
                local_unknown.add(rid)
        assert len(local_sent) == ledger['sent']
        assert len(local_settled) == ledger['settled']
        assert len(local_unknown) == ledger['unknown']
        assert len(local_sent) == len(local_settled) + len(local_unknown)
        assert ledger['inflight'] == 0
        u = tokenize(local_settled.values())
        close(u['list_cost_cny'], ledger['estimated_cost_cny_upper_bound'])
        assert u['input_tokens'] == ledger['tokens']['input_tokens']
        assert u['output_tokens'] == ledger['tokens']['output_tokens']
        batch_rows.append({'source': source, 'root': str(root), 'registered_scope': len(read(root / 'manifest.json')['cells']), 'attempt_records': len(outs), 'paid_attempts': sum(o['requests_sent'] > 0 for o in outs), 'sent': ledger['sent'], 'settled': ledger['settled'], 'unknown': ledger['unknown'], **u})
        history.extend((source, o) for o in outs)
    pairs = {(r['harness'], r['task_id']) for r in selection['rows']}
    assert len(pairs) == 354
    rows = [make_row(r['outcome'], r['selected_source'], selected=True) for r in selection['rows']]
    rows.sort(key=lambda r: (ORDER.index(r['harness']), r['task_id']))
    selected_ids = {r['trial_id'] for r in rows}
    all_rows = [make_row(o, source) for source, o in history]
    for row in all_rows:
        row['selected_for_matrix'] = row['trial_id'] in selected_ids
    assert len({r['trial_id'] for r in all_rows}) == len(all_rows)
    assert {r['trial_id'] for r in all_rows if r['selected_for_matrix']} == selected_ids
    summaries = [aggregate([r for r in rows if r['harness'] == h], h) for h in ORDER]
    assert all(s['trials'] == 59 for s in summaries)
    subgroup = [aggregate([r for r in rows if r['harness'] == h and r['task_group'] == g], h + ':' + g) for h in ORDER for g in ['C20', 'MS10', 'MP25', 'N4']]
    stage = [aggregate([r for r in rows if r['harness'] == h and r['stage'] == s], h + ':stage' + str(s)) for h in ORDER for s in [1, 2]]
    total = aggregate(rows, 'selected354')
    paid = [r for r in all_rows if r['requests_sent'] > 0]
    history_summary = []
    for h in ORDER:
        hs = [r for r in paid if r['harness'] == h]
        history_summary.append({'harness': h, 'paid_attempts': len(hs), 'selected_attempts': sum(r['selected_for_matrix'] for r in hs), 'superseded_paid_attempts': sum(not r['selected_for_matrix'] for r in hs), 'requests_sent': sum(r['requests_sent'] for r in hs), 'requests_settled': sum(r['requests_settled'] for r in hs), 'requests_unknown': sum(r['requests_unknown'] for r in hs), 'input_tokens': sum(r['input_tokens'] for r in hs), 'output_tokens': sum(r['output_tokens'] for r in hs), 'list_cost_cny_known_usage': sum(r['list_cost_cny'] for r in hs), 'actual_billed_cost_cny': None})
    anomalies = [r for r in rows if r['terminal_classification'] != 'normal_agent_exit' or r['integrity_ok'] is False]
    starts = [dt(r['started_at_utc']) for r in paid if r['started_at_utc']]
    finishes = [dt(r['finished_at_utc']) for r in paid if r['finished_at_utc']]
    audit = {
        'at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'selection_sha256': sha(SELECTION), 'reward_policy_sha256': sha(WORKSPACE / 'scoring/reward-policy-v1.0.json'),
        'original_manifest_sha256': sha(ROOT / BATCHES['original'] / 'manifest.json'),
        'dataset_sha256': manifest['dataset_sha256'],
        'selected_cells': len(rows), 'selected_unique_task_harness_pairs': len(pairs),
        'per_harness_cells': dict(collections.Counter(r['harness'] for r in rows)),
        'task_groups': dict(collections.Counter(r['task_group'] for r in rows if r['harness'] == 'codex')),
        'reward_difficulty': dict(collections.Counter(r['reward_difficulty'] for r in rows if r['harness'] == 'codex')),
        'empirical_difficulty': dict(collections.Counter(r['empirical_difficulty'] for r in rows if r['harness'] == 'codex')),
        'per_harness_max_reward': summaries[0]['max_reward_sum'],
        'reward_recomputed_and_matches': len(rows), 'score_hashes_checked': sum(r['score_hash_verified'] for r in rows),
        'resource_samples_verified': sum(r['resource_sample_count'] > 0 for r in rows),
        'selected_terminal_counts': dict(collections.Counter(r['terminal_classification'] for r in rows)),
        'selected_integrity_failed': sum(r['integrity_ok'] is False for r in rows),
        'selected_source_counts': dict(collections.Counter(r['selected_source'] for r in rows)),
        'all_attempt_records': len(all_rows), 'all_paid_attempts': len(paid), 'zero_send_records': len(all_rows) - len(paid),
        'superseded_paid_attempts': len(paid) - len(rows),
        'all_history_sent': sum(b['sent'] for b in batch_rows),
        'all_history_settled': sum(b['settled'] for b in batch_rows),
        'all_history_unknown': sum(b['unknown'] for b in batch_rows),
        'all_history_list_cost_cny_known_usage': sum(b['list_cost_cny'] for b in batch_rows),
        'all_history_input_tokens_known_usage': sum(b['input_tokens'] for b in batch_rows),
        'all_history_output_tokens_known_usage': sum(b['output_tokens'] for b in batch_rows),
        'first_paid_trial_started_at_beijing': min(starts).astimezone(timezone(timedelta(hours=8))).isoformat(),
        'last_paid_trial_finished_at_beijing': max(finishes).astimezone(timezone(timedelta(hours=8))).isoformat(),
        'elapsed_wall_seconds_between_first_and_last_paid_trial': (max(finishes) - min(starts)).total_seconds(),
        'settled_requests_verified_model_and_nonthinking': len(all_events),
        'actual_bill_available': False,
        'cost_definition': 'input_tokens*12/1e6+output_tokens*36/1e6 CNY; cache discount NOT applied; frozen Beijing list-price comparison, NOT Token Plan invoice',
        'unknown_requests': [{'trial_id': tid, 'request_ids': sorted(ids)} for tid, ids in UNKNOWN.items() if ids],
        'sources': source_proofs,
    }
    dump('selected-cells.json', rows)
    csv_out('selected-cells.csv', rows)
    dump('harness-summary.json', summaries)
    csv_out('harness-summary.csv', summaries)
    dump('dataset-summary.json', subgroup)
    csv_out('dataset-summary.csv', subgroup)
    dump('stage-summary.json', stage)
    csv_out('stage-summary.csv', stage)
    dump('all-attempts.json', all_rows)
    csv_out('all-attempts.csv', all_rows)
    dump('all-history-by-harness.json', history_summary)
    csv_out('all-history-by-harness.csv', history_summary)
    dump('batch-ledgers.json', batch_rows)
    csv_out('batch-ledgers.csv', batch_rows)
    dump('selected-anomalies.json', anomalies)
    csv_out('selected-anomalies.csv', anomalies)
    dump('totals.json', total)
    dump('audit.json', audit)
    print(json.dumps({'audit': {k:v for k,v in audit.items() if k not in ['sources','unknown_requests']}, 'summary': summaries, 'total': total}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
