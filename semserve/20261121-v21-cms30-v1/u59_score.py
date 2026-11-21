"""Upstream59 v2.1.0 delivery-bonus-50-v1 scoring for the 30-task C/MS modular replay.

Runs each task's official verifier (tests/test.sh) against the actor-produced
workspace in a fresh no-network container using the prebuilt :2.1 tests images,
then aggregates with the release scoring code (scoring/score_run.summarize).
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
BENCH = Path(r'C:\Users\yaohua xi\WorkBuddy\2026-11-20-11-28-54\benchmark')
VERIFIER_TIMEOUT = 2100


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def run_verifier(task, case):
    tag = f"u59-{task['id'].lower()}:2.1"
    logs = case / 'u59'
    logs.mkdir(parents=True, exist_ok=True)
    workspace = (case / 'workspace').resolve()
    volumes = ['-v', f"{workspace}:/app:ro", '-v', f"{logs.resolve()}:/logs/verifier"]
    completed = subprocess.run(
        ['docker', 'run', '--rm', '--network', 'none', *volumes, '--workdir', '/tests',
         tag, 'sh', 'test.sh'], capture_output=True, timeout=VERIFIER_TIMEOUT)
    output = (completed.stdout + completed.stderr).decode(errors='replace')
    (logs / 'container_output.txt').write_text(output, encoding='utf-8')
    if completed.returncode != 0:
        return dict(task=task['id'], status='verifier_error',
                    returncode=completed.returncode, stderr=output[-2000:])
    return read(logs / 'score.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()
    tasks = read(HERE / 'tasks.json')
    status = read(HERE / 'run_status.json')
    assert status['state'] == 'model_runs_complete'
    assert len(tasks) == 30
    scoring = BENCH / 'scoring'
    sys.path.insert(0, str(scoring))
    from score_run import summarize

    outcomes = []
    for task in tasks:
        actor = next(row for row in status['runs'] if row['task_id'] == task['id'])
        case = HERE / 'online' / actor['arm'] / 'cases' / task['entry_id'] / 'dynamic_v7'
        assert (case / 'workspace').is_dir(), case
        result = run_verifier(task, case)
        host = read(case / 'host_receipt.json')
        row = {key: result.get(key) for key in (
            'task', 'status', 'strict_pass', 'public_pass', 'integrity_ok',
            'passed_verifiers', 'total_verifiers', 'core_transform_cases_passed',
            'core_transform_cases_total', 'reward', 'max_reward',
            'robustness_all_passed', 'full_spec_pass')}
        row.update(actor_state=actor['state'], actor_seconds=host.get('actor_seconds'))
        outcomes.append(row)
        print('U59_SCORED', task['id'], row.get('status'), row.get('strict_pass'),
              row.get('reward'), flush=True)

    catalog = dict(version='2.1.0', scoring_revision='delivery-bonus-50-v1',
                   tasks=[dict(id=t['id']) for t in tasks],
                   max_total_reward=sum(r['max_reward'] for r in outcomes
                                        if r.get('max_reward') is not None))
    report = dict(state='complete', scoring_revision='delivery-bonus-50-v1',
                  benchmark_root=str(BENCH), network='none',
                  tasks=outcomes, summary=summarize(catalog, outcomes))
    save(HERE / 'u59_score_report.json', report)
    strict = report['summary']['strict_pass_count']
    covered = report['summary']['scored_tasks']
    print(f'U59_ALL_GRADED {covered} strict={strict} reward={report["summary"]["reward_sum_on_scored"]}',
          flush=True)


if __name__ == '__main__':
    main()
