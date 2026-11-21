"""Upstream59 v2.0.0 delivery-bonus-50-v1 scoring for the ten-task MP replay.

Builds the shared capstone-upstream59:2.0 base image and one tests image per task from
the local benchmark release checkout, runs each task's official verifier
(tasks/<ID>/tests/run_verifier.py) against the actor-produced workspace in a fresh,
no-network container, then aggregates with the release scoring code
(scoring/score_attempt.py + scoring/score_run.py summarize).

Run after score.py (which enforces that all model actors have stopped).
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
BENCH = Path(r'C:\Users\yaohua xi\WorkBuddy\2026-11-20-11-28-54\benchmark')
BASE_IMAGE = 'capstone-upstream59:2.0'
VERIFIER_TIMEOUT = 2100


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def docker(*args, timeout=None):
    return subprocess.run(['docker', *args], capture_output=True, timeout=timeout,
                          check=True)


def build_images(tasks):
    docker('build', '-t', BASE_IMAGE, '-f', str(BENCH / 'runtime' / 'Dockerfile'), str(BENCH),
           timeout=900)
    for task in tasks:
        tag = f"u59-{task['id'].lower()}:2.0"
        context = BENCH / 'tasks' / task['id'] / 'tests'
        docker('build', '-t', tag, str(context), timeout=600)
        print('BUILT', tag, flush=True)


def run_verifier(task, case):
    tag = f"u59-{task['id'].lower()}:2.0"
    logs = case / 'u59'
    logs.mkdir(parents=True, exist_ok=True)
    workspace = case / 'workspace'
    volumes = ['-v', f"{workspace}:/app:ro", '-v', f"{logs}:/logs/verifier"]
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
    parser.add_argument('--skip-build', action='store_true')
    args = parser.parse_args()
    plan = read(HERE / 'experiment_plan.json')
    tasks = read(HERE / 'tasks.json')
    status = read(HERE / 'run_status.json')
    assert status['state'] == 'model_runs_complete'
    assert len(tasks) == 10
    if not args.skip_build:
        build_images(tasks)
    scoring = Path(BENCH) / 'scoring'
    sys.path.insert(0, str(scoring))
    from score_run import summarize

    outcomes = []
    for task in tasks:
        actor = next(row for row in status['runs'] if row['task_id'] == task['id'])
        case = HERE / 'online' / actor['arm'] / 'cases' / task['entry_id'] / 'dynamic_v7'
        assert (case / 'workspace').is_dir(), case
        result = run_verifier(task, case)
        row = {key: result.get(key) for key in (
            'task', 'status', 'strict_pass', 'public_pass', 'integrity_ok',
            'passed_verifiers', 'total_verifiers', 'core_transform_cases_passed',
            'core_transform_cases_total', 'core_transform_case_pass_rate', 'reward',
            'max_reward', 'robustness_all_passed', 'full_spec_pass')}
        outcomes.append(row)
        print('U59_SCORED', task['id'], row.get('status'), row.get('strict_pass'),
              row.get('reward'), flush=True)

    catalog = dict(version='2.0.0', scoring_revision='delivery-bonus-50-v1',
                   tasks=[dict(id=t['id']) for t in tasks],
                   max_total_reward=sum(r['max_reward'] for r in outcomes
                                        if r.get('max_reward') is not None))
    report = dict(state='complete', scoring_revision='delivery-bonus-50-v1',
                  benchmark_root=str(BENCH), base_image=BASE_IMAGE,
                  network='none', tasks=outcomes, summary=summarize(catalog, outcomes))
    save(HERE / 'u59_score_report.json', report)
    strict = report['summary']['strict_pass_count']
    covered = report['summary']['scored_tasks']
    print(f'U59_ALL_GRADED {covered} strict={strict} reward={report["summary"]["reward_sum_on_scored"]}',
          flush=True)


if __name__ == '__main__':
    main()
