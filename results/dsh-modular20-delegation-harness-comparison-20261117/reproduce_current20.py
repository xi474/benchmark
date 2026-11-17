"""Reproduce the two current20 groups from published evidence, without model calls."""
from pathlib import Path
from decimal import Decimal
import csv, json

P = Path(__file__).resolve().parent
Q = P/'appendix/high20-current'
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
current = read(Q/'当前20题汇总.json')
original = read(Q/'历史附录/原32K与普通逐题汇总.json')
reruns = {r['task_id']: r for r in read(Q/'observations.json')['rows']}
assert set(reruns) == {'I06', 'K64', 'L114', 'M103', 'X13'}
assert read(Q/'最终验收.json')['audit_passed']
assert read(Q/'input-equivalence.json')['business_and_scorer_unchanged']
assert current['primary_results_use_reruns']
original_by = {(r['condition'], r['task_id']): r for r in original['per_task']}
fields = ['core_pass', 'core_total', 'public_pass', 'strict_pass', 'passed_verifiers',
          'total_verifiers', 'integrity_ok', 'reward', 'max_reward', 'child_count',
          'agent_sec', 'harbor_e2e_sec', 'input_tokens', 'output_tokens',
          'cache_tokens', 'common_peak_usd']
high = {r['task_id']: r for r in current['rows']}
ordinary = {r['task_id']: r for r in original['per_task'] if r['condition'] == 'ordinary'}
assert set(high) == set(ordinary) and len(high) == 20
for ident, row in high.items():
    source = reruns.get(ident, original_by['high', ident])
    assert row['rerun_applied'] == (ident in reruns)
    assert all(row[k] == source[k] for k in fields), ident

with (P/'普通与补跑后High逐题指标.csv').open(encoding='utf-8-sig', newline='') as f:
    csv_rows = list(csv.DictReader(f))
assert len(csv_rows) == 40
for group, records, condition in [(current['ordinary20'], ordinary, 'ordinary'),
                                  (current['current_high20'], high, 'high-current')]:
    for ident, row in records.items():
        reward = Decimal(row['passed_verifiers'])/Decimal(row['total_verifiers']) + int(row['strict_pass']) if row['integrity_ok'] else Decimal(0)
        assert abs(reward-Decimal(str(row['reward']))) < Decimal('.000001'), ident
        cached = Decimal(row['cache_tokens'])
        cost = ((Decimal(row['input_tokens'])-cached)*Decimal('1.32') + cached*Decimal('.044') + Decimal(row['output_tokens'])*Decimal('3.96'))/1000000
        assert abs(cost-Decimal(str(row['common_peak_usd']))) < Decimal('.00000001'), ident
        match = [r for r in csv_rows if r['condition'] == condition and r['task_id'] == ident]
        assert len(match) == 1
        for k in fields:
            if isinstance(row[k], bool):
                assert match[0][k].lower() == str(row[k]).lower()
            else:
                assert abs(Decimal(match[0][k])-Decimal(str(row[k]))) < Decimal('.00000001'), (ident,k)
    for key in ['strict_pass', 'public_pass', 'core_pass', 'core_total', 'reward',
                'max_reward', 'agent_sec', 'harbor_e2e_sec', 'input_tokens',
                'output_tokens', 'cache_tokens', 'common_peak_usd']:
        assert abs(sum(r[key] for r in records.values())-group[key]) < 1e-6, key
    assert sum(r['child_count'] for r in records.values()) == group['child_count'] == 0
    assert group['total_tokens'] == group['input_tokens']+group['output_tokens']
    assert abs(group['observed_e2e_plus_scoring_sec']-group['harbor_e2e_sec']-group['offline_scoring_supplement_sec']) < 1e-6
assert current['current_high20']['strict_pass'] == 15
assert current['current_high20']['core_pass'] == 192
assert current['current_high20']['reward'] == 32.125
assert current['ordinary20']['strict_pass'] == 14
assert current['ordinary20']['core_pass'] == 198
assert current['ordinary20']['reward'] == 31.4375
print(json.dumps(dict(passed=True, current20_groups=2, reward_rows=40,
                      reruns_applied=5, all_resource_rows_verified=True,
                      new_provider_calls=0, tasks_or_verifiers_changed=False)))
