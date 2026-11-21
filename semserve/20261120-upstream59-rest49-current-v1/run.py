"""Run the remaining 49 Upstream59 v2.0.0 tasks under the current frozen configuration (single ON arm, concurrency 4).

The 59-task release minus the ten tasks already replayed in
20261120-upstream59-mp10-current-v1 (MP01/03/05/12/16/17/18/19/20/26):
15 MP + 20 C + 10 MS + 4 N. Task inputs are taken directly from the local release
checkout (instruction.md + environment/workspace, byte-identical to the medium26 v5
sources for the MP tasks, verified at seal time). Scoring uses the release
delivery-bonus-50-v1 verifier (u59_score.py); the legacy medium26 scorer does not
cover the C/MS/N families.
"""

import argparse
import copy
import json
from pathlib import Path
import runpy
import shutil
import sys


HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
ON = RESULTS / '20261116-parallel20-profiles-current-first10-v1'
MP10 = RESULTS / '20261120-upstream59-mp10-current-v1'
PROFILE = RESULTS.parent / 'experiment_runtime_profile.json'
PLAN = HERE / 'experiment_plan.json'
TASKS = HERE / 'tasks.json'
STATUS = HERE / 'run_status.json'
PREFLIGHT = HERE / 'preflight.json'
NAMESPACES = HERE / 'cache_namespaces.json'
PREFIX = 'semserve-u59-rest49-v1-'
U59_RELEASE = Path(r'C:\Users\yaohua xi\WorkBuddy\2026-11-20-11-28-54\benchmark\tasks')
MANIFESTS = HERE / 'fixture_manifests'
MP_SOURCE = RESULTS / '20261108-medium26-current-v5-coverage-v1/experiment_plan.json'
CONCURRENCY = 4
# Packaging-layer shim for the component family (C/MS): the actor runtime's public-check
# gate hard-codes a root check.py (existence gate, output_guard "python3 check.py", and the
# final completion check). The release component workspaces expose public_check.py instead.
# The shim delegates 1:1 to the release checker; the official 59 verifier never runs it
# (its P item executes public_check.py / run_all.py --check in a fresh copy).
CHECK_SHIM = (
    "# Packaging shim (SemServe actor runtime compatibility): delegate to the release checker.\n"
    "import os\n"
    "import subprocess\n"
    "import sys\n"
    "\n"
    "raise SystemExit(subprocess.call(\n"
    "    [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public_check.py')]))\n"
)
DONE_MP10 = {'MP01', 'MP03', 'MP05', 'MP12', 'MP16', 'MP17', 'MP18', 'MP19', 'MP20', 'MP26'}
MP_ENTRIES = {
    'MP02': 'multistage4/single_axis_concat',
    'MP04': 'multistage4/multiformat_user_merge',
    'MP06': 'multistage4/calendar_cancel_notify',
    'MP07': 'linux2/send_archive_cleanup',
    'MP08': 'linux2/holiday_photo_migration',
    'MP09': 'reasoning4/panel_events_procurement',
    'MP10': 'context8/dinner_contact_checkout',
    'MP13': 'reasoning4/grouped_feature_union',
    'MP14': 'context8/portable_exception_report',
    'MP15': 'reasoning4/python_import_usage',
    'MP21': 'context8/playlist_query_export',
    'MP22': 'multistage4/marc_catalog_import',
    'MP23': 'linux2/reversible_file_resharding',
    'MP24': 'reasoning4/university_relation_query',
    'MP25': 'multistage4/text_invoice_archive',
}


def release_ids():
    ids = sorted(path.name for path in U59_RELEASE.iterdir() if path.is_dir())
    rest = [tid for tid in ids if tid not in DONE_MP10]
    assert len(rest) == 49, rest
    return rest


def driver():
    original = runpy.run_path(str(ON / 'run.py'))
    runner = original['driver']()
    baseline_on = original['validate'](runner)
    for key, value in dict(HERE=HERE, PREFIX=PREFIX, PLAN=PLAN, TASKS=TASKS,
                           STATUS=STATUS, PREFLIGHT=PREFLIGHT, NAMESPACES=NAMESPACES,
                           ARMS=('on',), CONCURRENCY=CONCURRENCY).items():
        setattr(runner, key, value)
    runner.cache_namespace.ARMS = ('on',)
    runner.task_mount = lambda task: HERE / 'actor_inputs' / task['id']
    # Mount the sealed per-task fixture manifest into the actor container.
    base_actor_options = runner.actor_options

    def actor_options_with_manifest(plan, cache, task, arm):
        options = base_actor_options(plan, cache, task, arm)
        manifest = MANIFESTS / (task['id'] + '.json')
        return [*options, *runner.path_mount(manifest, '/opt/fixture_manifest.json')]

    runner.actor_options = actor_options_with_manifest
    run_actor = runner.run_actor
    runner.run_actor = lambda plan, cache, settings, task, arm: run_actor(
        plan['arms'][arm], cache, settings, task, arm)
    return runner, baseline_on


def fixture_manifest(tid, *, materialize=False):
    """Protected set for one task, mirroring the official release verifier."""
    release = U59_RELEASE / tid
    registry = json.loads((release / 'tests' / 'release-registry.json').read_text(encoding='utf-8'))
    if registry['family'] == 'component':
        protected = sorted(json.loads(
            (release / 'tests' / 'registry.json').read_bytes())['protected'])
        # The actor-runtime check.py delegation shim is packaging infrastructure:
        # protect it exactly like the release protects its own checkers.
        protected = sorted(set(protected) | {'check.py'})
    elif registry['family'] == 'blind':
        catalog = json.loads((release / 'tests' / 'dataset' / 'verifier' / 'catalog.json').read_bytes())
        protected = sorted(catalog['tasks'][tid]['protected'])
    else:
        # Modular (MP): the placeholder classifier, identical to the MP10 replay.
        sys.path.insert(0, str(RESULTS.parent / 'experiments/handshake_speculation_v1_report_gate_v1'))
        try:
            from portable_task_fixtures import portable_fixture_paths
            fixed, _ = portable_fixture_paths(
                release / 'environment' / 'workspace')
        finally:
            sys.path.pop(0)
        protected = sorted(fixed)
    workspace = {path.relative_to(release / 'environment' / 'workspace').as_posix():
                 runner_sha(path) for path in sorted((release / 'environment' / 'workspace').rglob('*'))
                 if path.is_file()}
    if registry['family'] == 'component':
        workspace['check.py'] = runner_sha_text(CHECK_SHIM)
    assert set(protected) <= set(workspace), (tid, set(protected) - set(workspace))
    if materialize:
        MANIFESTS.mkdir(parents=True, exist_ok=True)
        target = MANIFESTS / (tid + '.json')
        body = json.dumps(dict(task=tid, family=registry['family'], protected=protected,
                               workspace=workspace), ensure_ascii=False, indent=2,
                          sort_keys=True) + '\n'
        target.with_suffix('.json.tmp').write_text(body, encoding='utf-8')
        target.with_suffix('.json.tmp').replace(target)
    return protected, workspace


def runner_sha(path):
    import hashlib
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def runner_sha_text(text):
    import hashlib
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def selected_tasks(runner, *, materialize=False):
    mp_plan = runner.load(MP_SOURCE)
    mp_by_entry = {row['entry_id']: row for row in mp_plan['tasks']}
    # MP04/08/09/10/24 were revised in adapted6-core-v3; the 59 release carries the
    # revised bytes, which differ from the medium26-extension-v1 plan. Only the
    # non-revised MP tasks are cross-checked against that plan.
    revised = {'MP04', 'MP08', 'MP09', 'MP10', 'MP24'}
    tasks = []
    for tid in release_ids():
        release = U59_RELEASE / tid
        family = json.loads((release / 'tests' / 'release-registry.json').read_text(encoding='utf-8'))['family']
        if tid in MP_ENTRIES:
            entry = MP_ENTRIES[tid]
            style, slug = entry.split('/')
        else:
            # The actor entry CLI restricts --group to the four medium26 group labels
            # (context8/linux2/multistage4/reasoning4); with --task-source the group is
            # only a result-path/label (no catalog coupling). Park every non-MP task
            # under 'context8/<TID>' so /results/<group>/<case>/<arm> == /results/<entry>/dynamic_v7.
            entry = f'context8/{tid}'
            style, slug = 'context8', tid
        workspace_files = {path.relative_to(release / 'environment' / 'workspace').as_posix():
                           runner.sha(path) for path in sorted((release / 'environment' / 'workspace').rglob('*'))
                           if path.is_file()}
        task_prompt_sha256 = runner.sha(release / 'instruction.md')
        # Release byte gate: instruction + every workspace file (authoritative).
        if tid in MP_ENTRIES and tid not in revised:
            source = mp_by_entry[entry]
            assert task_prompt_sha256 == source['task_prompt_sha256'], tid
            assert workspace_files == source['workspace_files'], tid
        destination = HERE / 'actor_inputs' / tid / entry
        if family == 'component':
            assert 'public_check.py' in workspace_files, tid
            workspace_files['check.py'] = runner_sha_text(CHECK_SHIM)
            if materialize:
                shim = destination / 'workspace' / 'check.py'
                shim.parent.mkdir(parents=True, exist_ok=True)
                shim.write_text(CHECK_SHIM, encoding='utf-8', newline='\n')
        if materialize:
            target = destination / 'TASK.md'
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(release / 'instruction.md', target)
            for name in workspace_files:
                if name == 'check.py' and family == 'component':
                    continue
                out = destination / 'workspace' / name
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(release / 'environment' / 'workspace' / name, out)
        tasks.append(dict(id=tid, task_id=tid, entry_id=entry, title=tid, dataset='upstream59',
                          style=style, slug=slug, task_source=str(destination),
                          task_prompt_sha256=task_prompt_sha256, workspace_files=workspace_files,
                          family=family,
                          provenance=dict(upstream59_release=str(release),
                                          medium26_source_plan=str(MP_SOURCE) if tid in MP_ENTRIES else None)))
    return tasks


def variant(runner, baseline_on, tasks):
    profile = runner.load(PROFILE)
    plan = copy.deepcopy(baseline_on)
    plan['mounts']['/opt/parallel20_actor_adapter.py'] = dict(
        path=str(HERE / 'actor_adapter.py'), sha256=runner.sha(HERE / 'actor_adapter.py'))
    plan['actor_environment']['SEMSERVE_COMPONENT_ENTRY_PROFILE'] = ''
    for name, value in profile['actor_environment'].items():
        assert plan['actor_environment'][name] == value, name
    assert plan['h3']['budget_characters'] == profile['h3']['input_max_chars']
    assert plan['h3']['restore_effective_batches'] == profile['h3']['restore_effective_batches']
    assert plan['h3']['c4_summary_every'] == profile['h3']['c4_summary_every']
    plan.update(task_total=len(tasks), planned_runs=len(tasks), semantic_parallel='on',
                tasks_sha256=runner.sha(TASKS), container_prefix=PREFIX,
                cache_namespace_sha256=runner.sha(NAMESPACES), max_concurrency=CONCURRENCY,
                fixture_manifests={task['id']: runner.sha(MANIFESTS / (task['id'] + '.json'))
                                   for task in tasks})
    arms = {'on': plan}
    manifests = {task['id']: runner.sha(MANIFESTS / (task['id'] + '.json')) for task in tasks}
    return dict(state='prepared', image=baseline_on['image'], image_id=baseline_on['image_id'],
                container_prefix=PREFIX, actor_limits=baseline_on['actor_limits'],
                max_concurrency=CONCURRENCY, task_total=49, planned_runs=49,
                actor_initial_step=0, tasks_sha256=runner.sha(TASKS), trusted={}, arms=arms,
                fixture_manifests=manifests,
                backend=baseline_on['backend'], runner_sha256=runner.sha(Path(__file__)),
                predictor_access_sha256=runner.sha(HERE / 'predictor_access.py'),
                cache_namespace_sha256=runner.sha(NAMESPACES),
                runtime_profile_sha256=runner.sha(PROFILE),
                actor_fixture_adapter_sha256=runner.sha(HERE / 'actor_adapter.py'),
                source_plans={'on': runner.sha(ON / 'experiment_plan.json')},
                treatment=dict(on='DeepSeek V4 Pro ordinary inference, semantic ON, Fork, value_v2 predictor'),
                selection='The remaining 49 Upstream59 v2.0.0 tasks after the 2026-11-20 MP10 replay: '
                          '15 MP + 20 C + 10 MS + 4 N, sourced byte-identically from the release checkout. '
                          'Non-MP tasks use the context8 group label for actor result paths only.',
                component_interface='Native legacy render.py interface for the medium26 dataset.',
                hidden_verifier_visible_to_actors=False, hidden_grading='after all model actors stop')


def prepare(runner, baseline_on):
    assert not PLAN.exists() and not TASKS.exists() and not STATUS.exists()
    for task_id in release_ids():
        fixture_manifest(task_id, materialize=True)
    tasks = selected_tasks(runner, materialize=True)
    runner.save(TASKS, tasks)
    runner.cache_namespace.prepare_namespaces([task['entry_id'] for task in tasks], experiment_dir=HERE)
    plan = variant(runner, baseline_on, tasks)
    runner.save(PLAN, plan)
    runs = [dict(arm=arm, task_id=task['id'], entry_id=task['entry_id'], state='pending', returncode=None)
            for arm, block in runner.interleaved_blocks(tasks) for task in block]
    runner.save(STATUS, dict(state='prepared', container_prefix=PREFIX, image_id=plan['image_id'],
                             plan_sha256=runner.sha(PLAN), runs=runs))
    validate(runner, baseline_on)
    print('SEALED_U59_REST49', len(tasks), len(runs), flush=True)


def validate(runner, baseline_on):
    tasks = selected_tasks(runner)
    plan = runner.load(PLAN)
    assert plan == variant(runner, baseline_on, tasks)
    assert runner.load(TASKS) == tasks
    assert all(runner.task_files(task) == runner.expected_task_files(task) for task in tasks)
    for task in tasks:
        protected, workspace = fixture_manifest(task['id'])
        manifest = runner.load(MANIFESTS / (task['id'] + '.json'))
        assert manifest['protected'] == protected, task['id']
        assert manifest['workspace'] == workspace, task['id']
        assert runner.sha(MANIFESTS / (task['id'] + '.json')) == plan['fixture_manifests'][task['id']]
    cache = runner.load(NAMESPACES)
    assert len(cache['slots']) == 49 and {row['arm'] for row in cache['slots']} == {'on'}
    prefixes = {row['prefix_sha256'] for row in cache['slots']}
    assert len(prefixes) == 49
    for path in RESULTS.glob('20261*/*/cache_namespaces.json'):
        try:
            older = runner.load(path)
        except Exception:
            continue
        if not isinstance(older, dict) or 'prefix_bytes' not in older or 'slots' not in older:
            continue
        assert (cache['prefix_bytes'], cache['prefix_tokens']) == (older['prefix_bytes'], older['prefix_tokens'])
        assert not prefixes.intersection(row['prefix_sha256'] for row in older['slots'])
    assert runner.docker('image', 'inspect', plan['image'], '--format', '{{.Id}}').stdout.decode().strip() == plan['image_id']
    for arm in plan['arms'].values():
        assert all(runner.sha(Path(row['path'])) == row['sha256'] for row in arm['mounts'].values())
    return plan


PROBE = '''
import hashlib,json,os,pathlib,runpy,sys
settings=json.load(sys.stdin)
sys.path[:0]=settings['import_paths']
runpy.run_path('/opt/e1_docker_entry.py')['enable']()
from parallel20_actor_adapter import fixture_paths,semantic_cli
from visible_contract_check_live import MAX_REVIEW_SECONDS
from agent_runtime_demo import medium30_component_entry,qwen_frontier_predictor
from agent_runtime_demo.runtime import AgentRuntime
from agent_runtime_demo.parallel_control_v2 import ConfigV2,ControllerV2,MockPredictorV2
from agent_runtime_demo.tools.registry import ToolRegistry
from agent_runtime_demo.tools.workspace import ReportFrontierStateTool
from agent_runtime_demo.types import RuntimeState
assert MAX_REVIEW_SECONDS==300 and not medium30_component_entry.enabled()
assert not pathlib.Path('/trusted').exists()
assert all(hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==digest for path,digest in settings['mounts'].items())
root=pathlib.Path('/opt/tasks')
assert {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}==settings['task_files']
base=root/settings['entry']
fixed,editable=fixture_paths(base/'workspace',(base/'TASK.md').read_text())
assert sorted(editable)==settings['expected_editable']
assert settings['checker'] in fixed
mode=os.environ['SEMSERVE_SEMANTIC_PARALLEL']
args=semantic_cli(['--parallel-v2','active'],mode)
assert args[1:]==(['active'] if mode=='on' else ['off','--no-subtasks'])
rt=AgentRuntime(object(),ToolRegistry([ReportFrontierStateTool()]),'official task instructions',parallel_controller_v2=ControllerV2(ConfigV2(mode='active'),MockPredictorV2()))
state=RuntimeState('verify frontier',[{'role':'system','content':'official task instructions'},{'role':'user','content':'verify frontier'}],step=2,run_id='probe',task_id='probe',inference_request_id='probe-request',inference_session_id='probe-session',v2_frontier_handshake_pending=True,v2_frontier_handshake_generation=1)
schema,=rt._model_tool_schemas(state)
required=schema['function']['parameters']['properties']['ready_upsert']['items']['required']
assert {'difficulty','length'} <= set(required)
print(json.dumps(dict(semantic_parallel=mode,editable=editable,protected=len(fixed),branch_profiles=True,native_legacy_components=True)))
'''


def _local_permissions(task):
    """Classify the materialized workspace with the sealed fixture manifest."""
    manifest = json.loads((MANIFESTS / (task['id'] + '.json')).read_bytes())
    workspace_root = HERE / 'actor_inputs' / task['id'] / task['entry_id'] / 'workspace'
    files = [p.relative_to(workspace_root).as_posix() for p in sorted(workspace_root.rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts]
    protected = set(manifest['protected'])
    return [name for name in files if name in protected], [name for name in files if name not in protected]


def _probe_expectations(task):
    fixed, editable = _local_permissions(task)
    assert editable, (task['id'], 'no editable placeholder found')
    checker = 'check.py' if task['id'].startswith(('MP', 'N')) else 'public_check.py'
    if checker not in fixed:
        checker = 'check.py' if 'check.py' in fixed else sorted(fixed)[0]
    return sorted(editable), checker


def preflight(runner, plan):
    tasks = runner.load(TASKS)
    cache = runner.load(NAMESPACES)
    by_id = {task['id']: task for task in tasks}
    sample = [by_id[tid] for tid in ('MP02', 'C008', 'MS02', 'N11')]
    receipts = []
    for task in sample:
        expected_editable, checker = _probe_expectations(task)
        options = runner.actor_options(plan['arms']['on'], cache, task, 'on')
        settings = dict(mounts={dest: row['sha256'] for dest, row in plan['arms']['on']['mounts'].items()},
                        task_files=runner.expected_task_files(task), entry=task['entry_id'],
                        expected_editable=expected_editable, checker=checker,
                        import_paths=[runner.SRC.rpartition('/')[0], runner.LIVE, '/opt',
                                      '/opt/semserve/' + runner.ROOT.name])
        command = ['run', '--rm', '--network', 'none', *options, '--entrypoint', 'python3']
        output = runner.docker(*command, '-i', plan['image_id'], '-c', PROBE,
                               data=json.dumps(settings).encode('utf8')).stdout
        receipt = json.loads(output.decode().splitlines()[-1])
        dry = runner.docker(*command, '-e', 'PARALLEL20_CACHE_DRY_RUN=1', plan['image_id'],
                            runner.cache_namespace.ACTOR_PATH).stdout
        receipt.update(task_id=task['id'], cold_namespace_mock=json.loads(dry.decode().splitlines()[-1]))
        receipts.append(receipt)
        print('OFFLINE_REST49_PREFLIGHT', task['id'], flush=True)
    runner.save(PREFLIGHT, dict(state='passed', model_calls=0, plan_sha256=runner.sha(PLAN), cases=receipts))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'preflight', 'predictor-preflight', 'run'))
    parser.add_argument('--tasks', nargs='+', help='Run a subset (smoke test), retaining the sealed plan')
    args = parser.parse_args()
    access = runpy.run_path(str(HERE / 'predictor_access.py'))
    runner, baseline_on = driver()
    if args.operation == 'prepare':
        prepare(runner, baseline_on)
        return
    plan = validate(runner, baseline_on)
    if args.operation == 'preflight':
        preflight(runner, plan)
    elif args.operation == 'predictor-preflight':
        access['preflight']()
    else:
        runner.upstream = lambda: access['upstream'](plan['backend'])
        runner.run(plan, args.tasks)


if __name__ == '__main__':
    main()
