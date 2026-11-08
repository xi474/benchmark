"""Build the versioned Medium20 exclusion view from immutable published results.

No model requests, task execution, score changes, task edits or verifier edits.
Run from any directory: python -B scripts/build_medium20.py
"""
import collections
import copy
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'medium20-revision-2026-11-09'
ARMS = ['nanobot', 'opencode', 'codex', 'dsh', 'langgraph',
        'latte-planning-adapted', 'roma', 'aorchestra']
DATASETS = {'original14': 14, 'mixed16-v4': 16, 'medium20': 20}
EXCLUSIONS = {
    'medium/MP04': ('多格式用户合并', '公开说明未明确records返回列表或字典，verifier要求列表。'),
    'medium/MP08': ('节日照片迁移', '概要要求指定年份，但组件未明确年份字段、路径提取或输入预筛选约定。'),
    'medium/MP09': ('座谈会与物资采购', '概要的下月第二个周日/最贵可用物资与组件的时段、评分和低价优先规则不一致。'),
    'medium/MP10': ('晚宴邀请与采购', '邀请两人与单联系人/recipient接口不一致；items、unavailable排序要求未公开明确。'),
    'medium/MP11': ('取消会面与图书采购', '概要要求精装书，但无装帧字段、筛选规则或输入已预筛选说明。'),
    'medium/MP24': ('大学任职查询', '概要要求正式教授，但无职称字段或professors列表已筛选说明。'),
}
SOURCE_FILES = [
    'seven-harnesses/results.json', 'aorchestra/results-56.json',
    'cache-analysis/results.json', 'seven-harnesses/self-check-loops.csv',
    'parallel-analysis/parallel-trigger-cells-392.csv',
]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n',
                    encoding='utf-8', newline='\n')


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def csv_save(path, rows):
    assert rows
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True)
                             if isinstance(v, (dict, list)) else v
                             for k, v in row.items()})


def sum_known(rows, key):
    values = [r[key] for r in rows if r.get(key) is not None]
    return sum(values) if values else None


def money(rows, key='estimated_settled_peak_usd'):
    values = [Decimal(str(r[key])) for r in rows if r.get(key) is not None]
    return float(sum(values)) if values else None


def rate(numerator, denominator):
    return numerator/denominator if numerator is not None and denominator else None


def normalize_seven(raw, hashes):
    row = copy.deepcopy(raw)
    row.update(source_dataset=raw['dataset'],
               dataset='medium20' if raw['dataset']=='medium26' else raw['dataset'],
               source_file='seven-harnesses/results.json',
               source_file_sha256=hashes['seven-harnesses/results.json'])
    row['quality_comparable'] = (row['score_status']=='scored' and
                                not row['api_accuracy_status'].startswith('unscored_'))
    row['usage_complete'] = row.get('tokens_input') is not None and row.get('tokens_output') is not None
    row['condition'] = 'selected-baseline; unchanged native/frozen/adapted and limit labels in historical report'
    return row


def normalize_ao(raw, hashes, resource_scope):
    ds = {'original':'original14', 'hard':'mixed16-v4', 'medium':'medium20'}[raw['task'].split('/')[0]]
    phases, tools = raw['phase_seconds'], raw['tool_concurrency']
    usage = raw['known_settled_usage']
    return dict(
        arm='aorchestra', task=raw['task'], dataset=ds,
        source_dataset='medium26' if ds=='medium20' else ds,
        trial_id=raw['trial'], classification=raw['quality_status'],
        certified_reward=raw['reward'], certified_max_reward=raw['max_reward'],
        score_status=raw['quality_status'], integrity_ok=raw['integrity_ok'],
        quality_comparable=raw['quality_eligible'],
        all_checks_passed=raw['passed_verifiers']==raw['total_verifiers'],
        overall_passed=raw['passed_verifiers'], overall_total=raw['total_verifiers'],
        api_passed=raw['api_passed'], api_total=raw['api_total'],
        api_accuracy=raw['api_accuracy'] if raw['api_comparable'] else None,
        api_accuracy_status='measured' if raw['api_comparable'] else 'not_applicable',
        focused_passed=raw.get('focused_passed'), focused_total=raw.get('focused_total'), focused_accuracy=raw.get('focused_accuracy'),
        e2e_seconds=raw['e2e_seconds'],
        agent_execution_seconds=phases.get('agent_execution'), verifier_seconds=phases.get('verifier'),
        environment_setup_seconds=phases.get('environment_setup'), agent_setup_seconds=phases.get('agent_setup'),
        model_requests_sent=raw['request_count'], model_requests_settled=raw['settled_count'],
        model_requests_unknown=raw['unknown_count'], model_requests_inflight=raw['inflight_count'],
        tokens_input=raw['input_tokens'], tokens_output=raw['output_tokens'],
        tokens_total=raw['input_tokens']+raw['output_tokens'] if None not in (raw['input_tokens'],raw['output_tokens']) else None,
        tokens_input_known=usage['input_tokens'], tokens_output_known=usage['output_tokens'],
        tokens_cache_hit_known=raw['cache_tokens'], cache_usage_complete=raw['cache_tokens'] is not None,
        tokens_status=raw['usage_status'],
        usage_complete=(raw['unknown_count']==0 and raw['inflight_count']==0
                        and raw['request_count']==raw['settled_count']
                        and usage['input_tokens'] is not None and usage['output_tokens'] is not None),
        tokens_source='provider-egress known_settled_usage; native summary missing remains separately labeled',
        estimated_settled_peak_usd=float(raw['known_settled_peak_usd']),
        orchestration_status=raw['orchestration_status'], orchestration_reason=raw['orchestration_reason'],
        observed_subagent_count_reported=raw['topology']['subagent_count'],
        tool_calls_reported=tools['tool_call_count'],
        tool_complete_span_count=tools['complete_span_count'],
        tool_failed_span_count=tools['failed_span_count'],
        tool_max_concurrent_tools=tools['max_concurrent_tools'],
        tool_observed_active_tool_time_ms=tools['observed_active_tool_time_ms'],
        tool_timing_quality='native monotonic paired spans',
        resource_samples=raw['resource_samples'],
        peak_sampled_container_memory_bytes=raw['maximum_memory_current_bytes'],
        container_cpu_delta_seconds=raw['cpu_usage_delta_seconds'], resource_scope=resource_scope,
        self_check_correlated_loops=None, delivery_sent=None, delivery_parent_received=None,
        delivery_entered_model_request=None,
        aorchestra_paired_summary_returns=raw.get('paired_summary_returns',raw['delegations']['returned']),
        aorchestra_parallel_agents_observed=raw['topology']['parallel_agents_observed'],
        aorchestra_original_usage_status=raw['usage_status'],
        source_file='aorchestra/results-56.json',
        source_file_sha256=hashes['aorchestra/results-56.json'],
        result_locator=raw['evidence_root'],
        condition='AOrchestra local-adapted; serial delegation; output4096/request160; original conditions preserved',
        native_metrics=copy.deepcopy(raw))


def summarize(rows, arm, dataset):
    good = [r for r in rows if r['quality_comparable']]
    api = [r for r in rows if r['api_accuracy'] is not None]
    focused = [r for r in rows if r.get('focused_accuracy') is not None]
    times = sorted(r['e2e_seconds'] for r in rows if r.get('e2e_seconds') is not None)
    complete_cache = all(r['cache_rate_status'] in ['observed','not_applicable_zero_input'] for r in rows)
    known_in, known_hit = (sum_known(rows,k) for k in ['tokens_input_known','tokens_cache_hit_known'])
    known_cache_rate = rate(known_hit, known_in) if all(r['cache_usage_complete'] for r in rows) else None
    full = [r for r in rows if r['cache_rate_status']=='observed']
    maximum = sum(r['certified_max_reward'] for r in good)
    reward_sum = money(good,'certified_reward')
    result = dict(
        arm=arm, dataset=dataset, cells=len(rows), quality_comparable_cells=len(good),
        invalid_submission_cells=sum(r['score_status']=='invalid_submission' for r in rows),
        unscored_cells=sum(not r['quality_comparable'] and r['score_status']!='invalid_submission' for r in rows),
        api_measured_cells=len(api), api_passed=sum(r['api_passed'] for r in api),
        api_total=sum(r['api_total'] for r in api),
        api_micro_accuracy=rate(sum(r['api_passed'] for r in api),sum(r['api_total'] for r in api)),
        api_macro_accuracy=statistics.mean(r['api_accuracy'] for r in api) if api else None,
        focused_measured_cells=len(focused),
        focused_micro_accuracy=rate(sum(r['focused_passed'] for r in focused if r.get('focused_passed') is not None),
                                    sum(r['focused_total'] for r in focused if r.get('focused_total') is not None)),
        reward_sum=reward_sum, reward_max_comparable=maximum,
        reward_normalized_comparable=rate(reward_sum,maximum),
        registered_max_reward_sum=sum(r['certified_max_reward'] for r in rows),
        raw_recorded_reward_sum=money(rows,'certified_reward'),
        full_reward_cells=sum(r['certified_reward']==r['certified_max_reward'] for r in good),
        full_reward_rate_comparable=rate(sum(r['certified_reward']==r['certified_max_reward'] for r in good),len(good)),
        all_checks_passed_cells=sum(r['all_checks_passed'] is True for r in good),
        classification_counts=dict(collections.Counter(r['classification'] for r in rows)),
        orchestration_status_counts=dict(collections.Counter(r['orchestration_status'] if r['orchestration_status'] is not None else 'unknown' for r in rows)),
        e2e_observed_cells=len(times), e2e_mean_seconds=statistics.mean(times) if times else None,
        e2e_median_seconds=statistics.median(times) if times else None,
        e2e_p95_nearest_rank_seconds=times[math.ceil(.95*len(times))-1] if times else None,
        e2e_trial_seconds_sum=sum(times) if times else None,
        tokens_input_known=known_in, tokens_output_known=sum_known(rows,'tokens_output_known'),
        tokens_cache_hit_known=known_hit, tokens_observed_cells=sum(r['usage_complete'] for r in rows),
        usage_partial_or_missing_cells=sum(not r['usage_complete'] for r in rows),
        model_requests_sent=sum_known(rows,'model_requests_sent'),
        model_requests_settled=sum_known(rows,'model_requests_settled'),
        unknown_requests=sum_known(rows,'model_requests_unknown'),
        estimated_settled_peak_usd=money(rows), invoice_usd=None,
        input_cache_hit_rate=known_cache_rate if complete_cache else None,
        observed_input_cache_hit_rate=known_cache_rate,
        input_cache_hit_rate_macro=statistics.mean(r['input_cache_hit_rate'] for r in full) if full else None,
        cache_rate_status='observed' if complete_cache else 'partial_or_missing',
        cache_measured_cells=len(full),
        cache_partial_cells=sum(r['cache_rate_status']=='partial_unknown_request' for r in rows),
        resource_observed_cells=sum((r.get('resource_samples') or 0)>0 for r in rows),
        container_memory_peak_bytes=max((r['peak_sampled_container_memory_bytes'] for r in rows if r.get('peak_sampled_container_memory_bytes') is not None),default=None),
        container_cpu_delta_seconds_sum=sum_known(rows,'container_cpu_delta_seconds'),
        tool_calls_known=sum_known(rows,'tool_calls_reported'),
        tool_time_observed_cells=sum(r.get('tool_observed_active_tool_time_ms') is not None for r in rows),
        tool_active_time_ms_sum=sum_known(rows,'tool_observed_active_tool_time_ms'),
        self_check_observed_cells=sum(r.get('self_check_correlated_loops') is not None for r in rows),
        self_check_correlated_loops=sum_known(rows,'self_check_correlated_loops'),
        child_count_observed_cells=sum(r.get('observed_subagent_count_reported') is not None for r in rows),
        tasks_with_reported_children=sum((r.get('observed_subagent_count_reported') or 0)>0 for r in rows),
        reported_children_sum=sum_known(rows,'observed_subagent_count_reported'),
        roma_child_solve_instances_sum=sum_known(rows,'roma_actual_child_solve_instances'),
        delivery_sent_known=sum_known(rows,'delivery_sent'),
        delivery_parent_received_known=sum_known(rows,'delivery_parent_received'),
        delivery_entered_model_request_known=sum_known(rows,'delivery_entered_model_request'),
        aorchestra_paired_summary_returns=sum_known(rows,'aorchestra_paired_summary_returns'))
    for phase in ['agent_execution_seconds','verifier_seconds','environment_setup_seconds','agent_setup_seconds']:
        values=[r[phase] for r in rows if r.get(phase) is not None]
        result[phase+'_mean']=statistics.mean(values) if values else None
        result[phase+'_observed_cells']=len(values)
    return result


def fmt(value, percentage=False, places=2):
    if value is None:
        return '不适用/未知'
    return f'{value:.{places}%}' if percentage else f'{value:,.{places}f}'


def report(groups, totals, excluded):
    medium=[g for g in groups if g['dataset']=='medium20']
    lines=['# Medium20修订统计：规格问题六题统一排除', '',
           '日期：2026-11-09。按用户的数据集规格裁决，将MP04、MP08、MP09、MP10、MP11、MP24从所有八套Harness的正式统计中统一排除。新增模型/API请求0，未重跑、改题、改verifier或改写任何旧分数。', '',
           '**当前正式分析集：原14题＋mixed16-v4的16题＋Medium20，共50题/臂，八臂400题位。** Medium20保留原题号，含MP01、MP02、MP03、MP05、MP06、MP07、MP12、MP13、MP14、MP15、MP16、MP17、MP18、MP19、MP20、MP21、MP22、MP23、MP25、MP26。400题位不是400正常完成或成功。', '',
           '这是基于已观察到的规格缺陷作出的事后质量排除，所有Harness使用同一排除名单，与分数高低无关。原Medium26及完整448题位仍作为历史审计留档；不把排除后指标变化解释为Harness能力提高或新的模型实验。保留20题不等于已完成难度重新标定，沿用原reward-v2上限仅用于本次可比统计。', '',
           '## 排除依据', '',
           '以下问题来自用户本轮规格质量裁决；本轮未重新运行五次校准试验，也未独立复现这些规格缺陷。其余20题不因本次过滤自动获得规格无歧义保证。', '',
           '| 原题号 | 任务 | 排除原因 |', '|---|---|---|']
    for task,(title,reason) in EXCLUSIONS.items():
        lines.append(f'| {task} | {title} | {reason} |')
    lines += ['', '## Medium20：质量与时间', '',
              '| Harness | 题位 | 可比评分题 | API通过/总数 | API微平均 | API宏平均 | reward/可比上限 | 平均E2E秒 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for g in medium:
        lines.append(f"| {g['arm']} | {g['cells']} | {g['quality_comparable_cells']} | {g['api_passed']}/{g['api_total']} | {fmt(g['api_micro_accuracy'],True)} | {fmt(g['api_macro_accuracy'],True)} | {g['reward_sum']:.6f}/{g['reward_max_comparable']:g} | {fmt(g['e2e_mean_seconds'])} |")
    lines += ['', 'API微平均为可比题api/通过数之和÷其分母之和；宏平均为逐题比例平均。原14题无api/分母，focused检查另列。登记总检查数不是API分母。LATTE的4个invalid_submission、ROMA MP14发送前预算跳过仍留在20个题位中，排除可比质量分母，不能伪装成API 0%；它们的实际时间、tokens和费用仍计入本保留集合的运行开销。Codex MP14超时带分保留原标签；其MP08输出上限带分因规格问题已移入排除附表。', '',
              'reward为已保存的reward-v2分数求和，分母为可比评分题的原难度上限之和；不是满分率。另列registered_max_reward_sum说明所有注册题位的上限，不能混用两个分母。', '',
              '## Medium20：已知用量、输入缓存与费用', '',
              '| Harness | 输入tokens | 输出tokens | 缓存命中tokens | 输入缓存命中率 | 估算峰价USD |',
              '|---|---:|---:|---:|---:|---:|']
    for g in medium:
        lines.append(f"| {g['arm']} | {g['tokens_input_known']:,} | {g['tokens_output_known']:,} | {g['tokens_cache_hit_known']:,} | {fmt(g['input_cache_hit_rate'],True)} | {g['estimated_settled_peak_usd']:.9f} |")
    lines += ['', '输入缓存命中率按sum(cache-hit input)/sum(input)计算，输出不进分母。实际API上下文缓存与服务端GPU内部K/V命中率不同，后者仍未知。费用沿用历史统一峰价估算：每百万input miss USD1.32、cache hit USD0.044、output USD3.96；未按峰谷时刻重计，不是账单。AOrchestra原生summary缺测与provider-egress已结算用量保持分层。', '',
              '## 八臂当前完整50题汇总', '',
              '| Harness | 保留题位 | API微平均（仅有API分母题） | 平均E2E秒 | 已知输入tokens | 已知输出tokens | 已知结算估算USD |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for g in totals:
        lines.append(f"| {g['arm']} | {g['cells']} | {fmt(g['api_micro_accuracy'],True)} | {fmt(g['e2e_mean_seconds'])} | {g['tokens_input_known']:,} | {g['tokens_output_known']:,} | {g['estimated_settled_peak_usd']:.9f} |")
    included_cost=money(totals)
    excluded_cost=money(excluded)
    lines += ['', f'400个当前题位已知结算统一峰价估算合计USD {included_cost:.9f}；48个规格排除题位仍实际发生USD {excluded_cost:.9f}。两者合计恢复原448题位USD {included_cost+excluded_cost:.9f}。LATTE四个mixed16独立补跑保持单列，不并入400题位或以上金额。历史其他中断/失败attempt及未知用量不在此合计，不能视为全账户消费。', '',
              'ROMA original/release_compatibility_program仍有1个真实未知请求，保留已知token下界、完整缓存率null及原异常标签；不能把未知当0。没有通过排除六题消除此类历史不确定性。', '',
              '## 文件与重算', '',
              '- [排除策略与保留题号](exclusion-policy.json)：用户裁决来源、原因及应用范围。',
              '- [Medium20逐题全指标CSV](medium20-cells-160.csv)；[八臂Medium20汇总CSV](medium20-summary-8.csv)。',
              '- [当前400题位全指标CSV](cells-400.csv)；[完整JSON](results.json)；[24组Harness×数据集汇总CSV](harness-dataset-summary-24.csv)；[八臂50题汇总CSV](harness-summary-8.csv)。',
              '- [Medium20逐题API矩阵](api-task-matrix-medium20-eight-arms.csv)；[API覆盖/分类矩阵](api-coverage-medium20-eight-arms.csv)；[逐题输入缓存率](input-cache-matrix-medium20-eight-arms.csv)；[缓存覆盖矩阵](cache-coverage-medium20-eight-arms.csv)。',
              '- [48个排除题位全指标CSV](excluded-cells-48.csv)：保留原trial、分数和异常，状态仅增加分析集排除标记；[排除题位开销汇总](excluded-summary-8.csv)。',
              '- [已过滤七臂自检关联窗口](self-check-loops.csv)；[已过滤七臂并行触发明细](parallel-trigger-cells-350.csv)。AOrchestra的原生工具、拓扑、摘要返回及资源指标见results.json各行native_metrics。',
              '- [离线生成器](../scripts/build_medium20.py)；[独立校验器](../scripts/validate_medium20.py)。分别执行可重现与验证，均不需要API key。', '',
              '## 比较限制', '',
              '所有每题原始指标、trial ID、来源hash和质量/编排终态不变。聚合只在当前保留集合内重算。E2E均值、各阶段时间、tokens、缓存、费用、资源、自检关联窗口以及工具/子执行单元计数均可在导出中追溯；不可观测项保留null，不能把未记录当0。', '',
              '跨题5/8并发、ROMA单Harbor/HTTP4和AOrchestra批次并发/限额不同。E2E为各自条件下观测，不是同资源加速排名；trial秒数之和不是整批墙钟时间。工具时间及自检关联窗口不包含全部模型分析/修复增量成本。', '',
              '子线程、固定队友、递归Solve、模型/HTTP/工具重叠分别属于不同观测层，不能把统一计数当相同多Agent能力。新导出保留原分层字段，不因排除题目重新推断自主委派、动态规划或GPU指标。LATTE始终为planning-adapted，纯native/frozen和SDK均未混入。', '',
              '本修订只更新分析集与运行汇报，不修改正式题、输入、verifier、reward政策或catalog。旧Medium26来源仍在上级历史目录；不要将实验汇报、来源审计或作者验证材料挂载给被测Agent。', '']
    return '\n'.join(lines)


def main():
    OUT.mkdir(exist_ok=True)
    hashes={name:digest(ROOT/name) for name in SOURCE_FILES}
    seven=read(ROOT/SOURCE_FILES[0]);ao=read(ROOT/SOURCE_FILES[1]);cache=read(ROOT/SOURCE_FILES[2])
    cache_index={(r['arm'],r['task']):r for r in cache['rows']}
    original=[normalize_seven(r,hashes) for r in seven['baseline_cells']]
    original += [normalize_ao(r,hashes,ao['resource_scope']) for r in ao['rows']]
    for row in original:
        c=cache_index[(row['arm'],row['task'])]
        for key in ['input_cache_hit_rate','observed_input_cache_hit_rate','cache_rate_status','cache_usage_complete']:
            row[key]=c[key]
        row['analysis_included']=row['task'] not in EXCLUSIONS
        row['analysis_exclusion_reason']=EXCLUSIONS[row['task']][1] if not row['analysis_included'] else None
        if not row['analysis_included']:
            row['dataset']='medium26-excluded-spec-quality'
    selected=[r for r in original if r['analysis_included']]
    excluded=[r for r in original if not r['analysis_included']]
    for rows in [selected,excluded]:
        order={'original14':0,'mixed16-v4':1,'medium20':2,'medium26-excluded-spec-quality':2}
        rows.sort(key=lambda r:(ARMS.index(r['arm']),order[r['dataset']],r['task']))
    assert len(selected)==400 and len(excluded)==48
    assert all(sum(r['arm']==a for r in selected)==50 for a in ARMS)
    medium=[r for r in selected if r['dataset']=='medium20']
    assert len(medium)==160
    groups=[summarize([r for r in selected if (r['arm'],r['dataset'])==(arm,ds)],arm,ds)
            for arm in ARMS for ds in DATASETS]
    totals=[summarize([r for r in selected if r['arm']==arm],arm,'all50') for arm in ARMS]
    excluded_groups=[summarize([r for r in excluded if r['arm']==arm],arm,'excluded-medium6') for arm in ARMS]
    policy=dict(schema='medium20-specification-quality-exclusion/1',date='2026-11-09',
                status='current analysis view; historical task files and scores unchanged',
                authority='user specification-quality ruling in this chat, 2026-11-09',
                basis='post hoc specification-quality exclusion, applied to every arm independent of reward',
                independent_spec_defect_reproduction_this_round=False,
                exclusions=[dict(task=t,title=v[0],reason=v[1]) for t,v in EXCLUSIONS.items()],
                included_medium_tasks=sorted({r['task'] for r in medium}),
                applies_to_harnesses=ARMS,source_medium_tasks=26,current_medium_tasks=20,
                source_selected_cells=448,current_selected_cells=400,excluded_selected_cells=48,
                source_publication_commit='15cff22036137a153d516859323ea4f52e910c0f',
                source_sha256=hashes,renumber_tasks=False,task_files_modified=False,
                verifier_modified=False,scores_modified=False,new_trials=0,provider_requests=0,
                final_difficulty_calibrated=False,
                future_reinclusion_policy='clarify/version task and verifier first; separately authorize any new experiment; retain originals')
    save(OUT/'exclusion-policy.json',policy)
    metadata=dict(schema='v4pro-reward-v2-medium20-revision/1',date='2026-11-09',
                  current_cohort='8 arms x (original14 + mixed16-v4 + medium20) = 400 selected cells',
                  source_cohort='448 historical selected cells; immutable sources',
                  exclusion_policy_sha256=digest(OUT/'exclusion-policy.json'),source_sha256=hashes,
                  provider_requests=0,rows=selected,excluded_rows=excluded,
                  dataset_summary=groups,harness_summary=totals,excluded_summary=excluded_groups,
                  latte_independent_repeats=seven['latte_independent_repeats'])
    save(OUT/'results.json',metadata)
    for name,rows in [('cells-400.csv',selected),('medium20-cells-160.csv',medium),
                      ('excluded-cells-48.csv',excluded),('harness-dataset-summary-24.csv',groups),
                      ('medium20-summary-8.csv',[g for g in groups if g['dataset']=='medium20']),
                      ('harness-summary-8.csv',totals),('excluded-summary-8.csv',excluded_groups)]:
        csv_save(OUT/name,rows)
    save(OUT/'harness-dataset-summary-24.json',groups)
    for name,metric in [('api-task-matrix-medium20-eight-arms.csv','api_accuracy'),
                        ('api-coverage-medium20-eight-arms.csv','api_accuracy_status'),
                        ('input-cache-matrix-medium20-eight-arms.csv','input_cache_hit_rate'),
                        ('cache-coverage-medium20-eight-arms.csv','cache_rate_status')]:
        matrix=[]
        for task in policy['included_medium_tasks']:
            by_arm={r['arm']:r for r in medium if r['task']==task}
            matrix.append(dict(task=task,**{arm:by_arm[arm][metric] for arm in ARMS}))
        csv_save(OUT/name,matrix)
    for source,name in [(SOURCE_FILES[3],'self-check-loops.csv'),
                        (SOURCE_FILES[4],'parallel-trigger-cells-350.csv')]:
        rows=[r for r in read_csv(ROOT/source) if r['task'] not in EXCLUSIONS]
        for r in rows:
            if r['dataset']=='medium26':r['dataset']='medium20'
        if name.startswith('parallel'):assert len(rows)==350
        csv_save(OUT/name,rows)
    (OUT/'README.md').write_text(report(groups,totals,excluded),encoding='utf-8',newline='\n')
    generated=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!='revision-audit.json')
    save(OUT/'revision-audit.json',dict(schema='medium20-offline-revision-audit/1',
                                      source_sha256=hashes,
                                      artifact_sha256={p.name:digest(p) for p in generated},
                                      build_script_sha256=digest(Path(__file__)),
                                      current_cells=400,medium_cells=160,excluded_cells=48,
                                      original_scores_unchanged=True,provider_requests=0))
    print(json.dumps(dict(status='generated',selected_cells=400,medium20_cells=160,
                          excluded_cells=48,summary_groups=len(groups),
                          selected_known_peak_usd=money(totals),
                          excluded_known_peak_usd=money(excluded),provider_requests=0)))


if __name__=='__main__':
    main()
