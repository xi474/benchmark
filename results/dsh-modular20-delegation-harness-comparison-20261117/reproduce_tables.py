"""Offline consistency check of the published aggregate evidence. No API calls.

Checks arithmetic and consistency of supplied records, not model re-execution.
"""
from pathlib import Path
from decimal import Decimal
from collections import defaultdict
import csv, hashlib, json, sys

P = Path(__file__).resolve().parent
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
metrics = read(P/'unified-metrics.json')
by_group = defaultdict(list)
with (P/'同10题逐题统一reward.csv').open(encoding='utf-8-sig', newline='') as f:
    for r in csv.DictReader(f):
        strict = r['strict_pass'].lower() == 'true'
        expected = Decimal(r['passed_verifiers'])/Decimal(r['total_verifiers'])+int(strict)
        assert expected == Decimal(r['reward']), r['task_id']
        by_group[r['group']].append(r)
assert len(by_group)==4 and all(len(v)==10 for v in by_group.values())
for r in metrics['same10']:
    records=by_group[r['group']]
    assert sum(Decimal(v['reward']) for v in records)==Decimal(str(r['reward']))
    assert sum(v['strict_pass'].lower()=='true' for v in records)==r['strict_pass']
    assert abs(r['core_pass']/r['core_total']-r['core_rate'])<1e-12
    if r['group_key']=='DSH':
        resources=read(P/'resource-comparison.json')['dsh']
        cache=resources['cache_tokens']
    else:
        cache=Decimal(r['input_tokens'])*Decimal(str(r['cache_hit_ratio']))
    cost=((Decimal(r['input_tokens'])-cache)*Decimal('1.32')+cache*Decimal('.044')+Decimal(r['output_tokens'])*Decimal('3.96'))/1000000
    assert abs(float(cost)-r['common_peak_usd'])<1e-9
for r in metrics['m103_pair']:
    cost=((r['input_tokens']-r['cached_input_tokens'])*Decimal('1.32')+r['cached_input_tokens']*Decimal('.044')+r['output_tokens']*Decimal('3.96'))/1000000
    assert abs(float(cost)-r['common_peak_usd'])<1e-10
    assert r['reward']==2 and r['strict_pass']==1
checksum_file=P/'SHA256SUMS'
if checksum_file.exists() and '--metrics-only' not in sys.argv:
    for line in checksum_file.read_text(encoding='utf-8').splitlines():
        digest, name=line.split(None,1)
        assert hashlib.sha256((P/name.strip()).read_bytes()).hexdigest()==digest, name
print(json.dumps(dict(passed=True, tasks_per_group=10, groups=4, reward_rows=40, m103_pair=2,
                      new_provider_calls=0, original_task_and_score_changes=0)))
