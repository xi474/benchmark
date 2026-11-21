"""Ten-task Upstream59 replay under the current frozen configuration (single ON arm).

Selection: the ten highest-reward never-strictly-passing (empirical H) tasks among the
25 Medium26 tasks present in the Upstream59 v2.0.0 release (MP01-MP26 excluding MP11,
which is not published). Five-round calibration rewards (max 2):

    MP01 1.92  MP20 1.85  MP17 1.84  MP16 1.84  MP26 1.80
    MP12 1.79  MP05 1.75  MP18 1.72  MP03 1.69  MP19 1.65

Byte identity with the 59 release (instruction.md / environment/workspace) was verified
by SHA-256 before sealing; the replay is scored both by the legacy medium26 verifier and
by the new Upstream59 delivery-bonus-50-v1 weighted scorer (see u59_score.py).
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
PROFILE = RESULTS.parent / 'experiment_runtime_profile.json'
PLAN = HERE / 'experiment_plan.json'
TASKS = HERE / 'tasks.json'
STATUS = HERE / 'run_status.json'
PREFLIGHT = HERE / 'preflight.json'
NAMESPACES = HERE / 'cache_namespaces.json'
PREFIX = 'semserve-u59-mp10-v1-'
SELECTION = (
    ('MP01', 'medium26', 'multistage4/weighted_voting', '可关闭成员的硬/软加权投票'),
    ('MP03', 'medium26', 'multistage4/offline_mount_facts', '三种挂载格式的离线事实归并'),
    ('MP05', 'medium26', 'multistage4/cross_app_contact_ranking', '跨应用候选并集与相处时长排名'),
    ('MP12', 'medium26', 'linux2/files_mail_workspace', '下载目录归档、邮件清理与目标回复'),
    ('MP16', 'medium26', 'context8/api_documentation_merge', 'API 文档的签名、参数与继承信息聚合'),
    ('MP17', 'medium26', 'context8/multipart_encoding', '文本、内联内容和文件的 multipart 组装'),
    ('MP18', 'medium26', 'linux2/collection_manifest', '集合文件清单的指令选择与归档元数据'),
    ('MP19', 'medium26', 'reasoning4/module_dependency_zip', 'Python 支持模块发现与可重复 ZIP 载荷'),
    ('MP20', 'medium26', 'multistage4/feature_config_snapshot', '特性配置的模式、附件与引用一致性'),
    ('MP26', 'medium26', 'reasoning4/recurring_dinner_calendar', '每日晚餐提醒的去重、冲突取消与通知'),
)
SOURCES = {
    'medium26': RESULTS / '20261108-medium26-current-v5-coverage-v1/experiment_plan.json',
}
U59_RELEASE = Path(r'C:\Users\yaohua xi\WorkBuddy\2026-11-20-11-28-54\benchmark\tasks')


def driver():
    original = runpy.run_path(str(ON / 'run.py'))
    runner = original['driver']()
    baseline_on = original['validate'](runner)
    for key, value in dict(HERE=HERE, PREFIX=PREFIX, PLAN=PLAN, TASKS=TASKS,
                           STATUS=STATUS, PREFLIGHT=PREFLIGHT, NAMESPACES=NAMESPACES,
                           ARMS=('on',)).items():
        setattr(runner, key, value)
    runner.cache_namespace.ARMS = ('on',)
    runner.task_mount = lambda task: HERE / 'actor_inputs' / task['id']
    run_actor = runner.run_actor
    runner.run_actor = lambda plan, cache, settings, task, arm: run_actor(
        plan['arms'][arm], cache, settings, task, arm)
    return runner, baseline_on


def selected_tasks(runner, *, materialize=False):
    sources = {key: runner.load(path) for key, path in SOURCES.items()}
    tasks, trusted = [], {}
    for task_id, dataset, entry, title in SELECTION:
        source_plan = sources[dataset]
        task = next(row for row in source_plan['tasks'] if row['entry_id'] == entry)
        case = next(row for row in source_plan['cases'] if row['entry'] == entry)
        files = {'TASK.md': task['task_prompt_sha256'],
                 **{'workspace/' + name: digest for name, digest in task['workspace_files'].items()}}
        origin = Path(task['task_source'])
        destination = HERE / 'actor_inputs' / task_id / entry
        # Upstream59 v2.0.0 byte-identity gate (the "find the matching tasks in 59" step).
        release = U59_RELEASE / task_id
        assert runner.sha(release / 'instruction.md') == task['task_prompt_sha256'], task_id
        for name, digest in task['workspace_files'].items():
            assert runner.sha(release / 'environment' / 'workspace' / name) == digest, (task_id, name)
        for name, digest in files.items():
            assert runner.sha(origin / name) == digest, (task_id, name)
            if materialize:
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(origin / name, target)
        tasks.append(dict(id=task_id, task_id=task_id, entry_id=entry, title=title, dataset=dataset,
                          style=entry.split('/')[0], slug=entry.split('/')[1],
                          task_source=str(destination), task_prompt_sha256=task['task_prompt_sha256'],
                          workspace_files=task['workspace_files'], trusted_revision=case['trusted_revision'],
                          provenance=dict(source_plan=str(SOURCES[dataset]),
                                          source_plan_sha256=runner.sha(SOURCES[dataset]),
                                          source_task=str(origin),
                                          upstream59_release=str(U59_RELEASE / task_id),
                                          upstream59_byte_identical=True)))
        revision = case['trusted_revision']
        trusted[revision] = source_plan['trusted'][revision]
    return tasks, trusted


def variant(runner, baseline_on, tasks, trusted):
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
                cache_namespace_sha256=runner.sha(NAMESPACES))
    arms = {'on': plan}
    return dict(state='prepared', image=baseline_on['image'], image_id=baseline_on['image_id'],
                container_prefix=PREFIX, actor_limits=baseline_on['actor_limits'],
                max_concurrency=baseline_on['max_concurrency'], task_total=10, planned_runs=10,
                actor_initial_step=0, tasks_sha256=runner.sha(TASKS), trusted=trusted, arms=arms,
                backend=baseline_on['backend'], runner_sha256=runner.sha(Path(__file__)),
                predictor_access_sha256=runner.sha(HERE / 'predictor_access.py'),
                cache_namespace_sha256=runner.sha(NAMESPACES),
                runtime_profile_sha256=runner.sha(PROFILE),
                actor_fixture_adapter_sha256=runner.sha(HERE / 'actor_adapter.py'),
                source_plans={'on': runner.sha(ON / 'experiment_plan.json')},
                treatment=dict(on='DeepSeek V4 Pro ordinary inference, semantic ON, Fork, value_v2 predictor'),
                selection='Ten highest-reward never-strictly-passing Medium26 tasks present in the '
                          'Upstream59 v2.0.0 release (five-round mean reward 1.65-1.92 of 2): '
                          'MP01/03/05/12/16/17/18/19/20/26; byte identity with the release verified '
                          'by SHA-256 for instruction and every workspace file.',
                component_interface='Native legacy render.py interface for the medium26 dataset.',
                hidden_verifier_visible_to_actors=False, hidden_grading='after all model actors stop')


def prepare(runner, baseline_on):
    assert not PLAN.exists() and not TASKS.exists() and not STATUS.exists()
    tasks, trusted = selected_tasks(runner, materialize=True)
    runner.save(TASKS, tasks)
    runner.cache_namespace.prepare_namespaces([task['entry_id'] for task in tasks], experiment_dir=HERE)
    plan = variant(runner, baseline_on, tasks, trusted)
    runner.save(PLAN, plan)
    runs = [dict(arm=arm, task_id=task['id'], entry_id=task['entry_id'], state='pending', returncode=None)
            for arm, block in runner.interleaved_blocks(tasks) for task in block]
    runner.save(STATUS, dict(state='prepared', container_prefix=PREFIX, image_id=plan['image_id'],
                             plan_sha256=runner.sha(PLAN), runs=runs))
    validate(runner, baseline_on)
    print('SEALED_U59_MP10', len(tasks), len(runs), flush=True)


def validate(runner, baseline_on):
    tasks, trusted = selected_tasks(runner)
    plan = runner.load(PLAN)
    assert plan == variant(runner, baseline_on, tasks, trusted)
    assert runner.load(TASKS) == tasks
    assert all(runner.task_files(task) == runner.expected_task_files(task) for task in tasks)
    cache = runner.load(NAMESPACES)
    assert len(cache['slots']) == 10 and {row['arm'] for row in cache['slots']} == {'on'}
    prefixes = {row['prefix_sha256'] for row in cache['slots']}
    assert len(prefixes) == 10
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
assert 'check.py' in fixed and 'run_all.py' not in fixed and 'final_report.py' not in fixed
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


def preflight(runner, plan):
    tasks = runner.load(TASKS)
    cache = runner.load(NAMESPACES)
    receipts = []
    for task in tasks:
        options = runner.actor_options(plan['arms']['on'], cache, task, 'on')
        settings = dict(mounts={dest: row['sha256'] for dest, row in plan['arms']['on']['mounts'].items()},
                        task_files=runner.expected_task_files(task), entry=task['entry_id'],
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
        print('OFFLINE_MP10_PREFLIGHT', task['id'], flush=True)
    runner.save(PREFLIGHT, dict(state='passed', model_calls=0, plan_sha256=runner.sha(PLAN), cases=receipts))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'preflight', 'predictor-preflight', 'run'))
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
        runner.run(plan, None)


if __name__ == '__main__':
    main()
