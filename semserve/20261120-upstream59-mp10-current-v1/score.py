"""Score the ten-task Upstream59 MP replay (single ON arm) after all model actors stop.

Legacy medium26 verifier scoring (comparable with the five-round calibration history);
the Upstream59 delivery-bonus-50-v1 weighted scoring runs separately in u59_score.py.
"""

from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
from pathlib import Path
import runpy
import subprocess
import sys


HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
ARMS = ('on',)
TERMINAL = {'completed', 'failed', 'timed_out', 'cancelled'}
PUBLIC_WORKER = r'''
import json, pathlib, shutil, subprocess, sys
root = pathlib.Path('/tmp/candidate')
shutil.copytree('/archive', root, symlinks=True)
out = root / 'outputs'
if out.is_dir() and not out.is_symlink():
    shutil.rmtree(out)
try:
    process = subprocess.run([sys.executable, '-B', 'check.py'], cwd=root,
                             capture_output=True, timeout=240)
    print(json.dumps({'public_pass': process.returncode == 0,
                      'returncode': process.returncode}))
except subprocess.TimeoutExpired:
    print(json.dumps({'public_pass': False, 'returncode': None, 'timeout': True}))
'''


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines()
            if line.strip()] if Path(path).is_file() else []


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def stopped(plan, status, tasks):
    assert status['state'] == 'model_runs_complete', 'Wait for all model actors before grading'
    expected = {(arm, task['id']) for arm in ARMS for task in tasks}
    actual = {(row['arm'], row['task_id']) for row in status['runs']}
    assert actual == expected and len(status['runs']) == len(expected)
    assert all(row['state'] in TERMINAL for row in status['runs'])
    prefixes = {plan['container_prefix']}
    prefixes.update(arm['container_prefix'] for arm in plan.get('arms', {}).values()
                    if isinstance(arm, dict) and arm.get('container_prefix'))
    active = subprocess.check_output(['docker', 'ps', '--format', '{{.Names}}'],
                                     encoding='utf-8', timeout=30).splitlines()
    assert not any(name.startswith(prefix) for name in active for prefix in prefixes)
    for item in plan['trusted'].values():
        for relative, digest in item['sha256'].items():
            assert sha(Path(item['path']) / relative) == digest, relative


def medium_context(trusted, entries):
    medium = runpy.run_path(str(RESULTS / '20261106-medium26-current-memo-v1/report.py'))
    verifier = medium['load_verifier'](trusted)
    registry = {f"{task['style']}/{task['slug']}": task for task in verifier.TASKS}
    seals = read(trusted / 'verifier/protected_hashes.json')
    contexts = {}
    for entry in entries:
        source = registry[entry]
        contexts[entry] = dict(verifier=verifier, task=source, seal=seals[entry],
                               catalog=medium['case_catalog'](verifier, source), trusted=trusted)
    return contexts


def medium_grade(plan, task, case, context, medium):
    strict, components = medium['score'](context['verifier'], task['entry_id'], context['task'],
        context['catalog'], context['seal'], plan['image_id'], context['trusted'], case / 'workspace')
    assert strict['status'] in ('passed', 'failed'), strict
    public = medium['docker_job'](plan['image_id'], case / 'workspace',
        (context['trusted'] / 'verifier/probe.py', '/probe.py'), ['-c', PUBLIC_WORKER])
    assert public.returncode == 0, public.stderr[-800:]
    replay = json.loads(public.stdout.strip().splitlines()[-1])
    api = medium['api_summary'](components.values())
    grade = dict(public_pass=replay['public_pass'], strict_pass=strict['status'] == 'passed',
        official=strict, public_replay=replay, core_transform_passed=api['api_passed'],
        core_transform_total=api['api_total'], api_unexecuted=api['api_unexecuted'],
        api_components=components)
    if grade['strict_pass']:
        assert grade['public_pass'] and grade['core_transform_passed'] == grade['core_transform_total']
    save(case / 'external_validation.json', strict)
    return grade


def wire_audit(case, arm):
    wires = [row for row in rows(case / 'wire_requests.jsonl')
             if row.get('endpoint_host') == 'api.deepseek.com']
    enabled = arm == 'off'
    assert wires and all((row.get('requested_thinking') or {}).get('type') ==
                         ('enabled' if enabled else 'disabled') for row in wires)
    return dict(deepseek_requests=len(wires), thinking='enabled' if enabled else 'disabled',
                reasoning_effort='low' if enabled else None)


def evaluate_task(task_id):
    """Use one fresh process for each task's verifier metadata imports."""
    plan = read(HERE / 'experiment_plan.json')
    tasks = read(HERE / 'tasks.json')
    status = read(HERE / 'run_status.json')
    stopped(plan, status, tasks)
    selected = [task for task in tasks if task['id'] == task_id]
    assert len(selected) == 1
    task = selected[0]
    helper = runpy.run_path(str(RESULTS / '20261116-parallel20-semantic-ab-v1/score.py'))
    metric = runpy.run_path(str(helper['AUDIT']))
    cache = runpy.run_path(str(RESULTS / '20261116-parallel20-semantic-ab-v1/cache_namespace.py'))
    medium = runpy.run_path(str(RESULTS / '20261106-medium26-current-memo-v1/report.py'))
    revision = task['trusted_revision']
    contexts = medium_context(Path(plan['trusted'][revision]['path']), [task['entry_id']])
    manifest = read(HERE / 'cache_namespaces.json')

    def evaluate(actor):
        case = HERE / 'online' / actor['arm'] / 'cases' / task['entry_id'] / 'dynamic_v7'
        assert case.resolve().is_relative_to((HERE / 'online').resolve())
        assert (case / 'workspace').is_dir(), case
        grade = medium_grade(plan, task, case, contexts[task['entry_id']], medium)
        metrics, _, error = helper['measure'](case, metric)
        assert error is None, error
        protocol = helper['protocol'](case, metric, actor['arm'])
        assert protocol['mode_matches_arm'], protocol
        cold = helper['cold_namespace'](case, task, actor['arm'], actor, manifest, cache['audit_case'])
        # Deviation note: MP01/MP03 first DeepSeek requests hit a transient URLError and were
        # retried by the runner (wire_ordinal 3 succeeded). The strict audit reports
        # first_provider_usage_unavailable, but coldness is still evidenced by the first
        # successful receive (prompt_cache_hit_tokens == 0). Accept only that case.
        if cold['state'] == 'first_provider_usage_unavailable':
            iso = rows(case / 'deepseek_cache_isolation.jsonl')
            with_usage = [row for row in iso if row.get('event') != 'send'
                          and row.get('prompt_cache_hit_tokens') is not None]
            assert with_usage and with_usage[0]['prompt_cache_hit_tokens'] == 0, task['id']
            cold = dict(cold, state='verified_cold_after_transient_retry',
                        first_successful_request_cache_hit_tokens=with_usage[0]['prompt_cache_hit_tokens'],
                        first_successful_request_cache_miss_tokens=with_usage[0]['prompt_cache_miss_tokens'])
        assert cold['state'] in ('verified_cold', 'verified_cold_after_transient_retry')
        assert cold['reconciled_with_wire_audit']
        wire = wire_audit(case, actor['arm'])
        row = dict(task_id=task['id'], entry_id=task['entry_id'], title=task['title'],
            dataset=task['dataset'], arm=actor['arm'], case=str(case), actor_state=actor['state'],
            grade=grade, metrics=metrics, protocol=protocol, cold_namespace=cold, wire_audit=wire,
            scoring_error=None, metrics_error=None, protocol_error=None)
        save(case / 'task_measurement.json', row)
        print('SCORED', task['id'], actor['arm'], grade['public_pass'], grade['strict_pass'],
              f"{grade['core_transform_passed']}/{grade['core_transform_total']}", flush=True)
        return row

    actors = [actor for actor in status['runs'] if actor['task_id'] == task_id]
    assert {actor['arm'] for actor in actors} == set(ARMS) and len(actors) == 1
    return [evaluate(actor) for actor in actors]


def main():
    plan = read(HERE / 'experiment_plan.json')
    tasks = read(HERE / 'tasks.json')
    status = read(HERE / 'run_status.json')
    assert len(tasks) == 10 and len({task['id'] for task in tasks}) == 10
    stopped(plan, status, tasks)
    with ProcessPoolExecutor(max_workers=2, max_tasks_per_child=1,
                             mp_context=multiprocessing.get_context('spawn')) as executor:
        groups = list(executor.map(evaluate_task, [task['id'] for task in tasks]))
    result = [row for group in groups for row in group]
    report = dict(state='complete', task_total=10, run_total=10, tasks=result,
                  image_id=plan['image_id'], plan_sha256=sha(HERE / 'experiment_plan.json'),
                  hidden_feedback=False, grading='All actors stopped; original isolated no-network verifiers')
    save(HERE / 'score_report.json', report)
    print('ALL_MP10_GRADED', len(result), flush=True)


if __name__ == '__main__':
    main()
