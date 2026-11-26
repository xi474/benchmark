"""Build shareable, entirely offline report artifacts from audited JSON."""
import csv
import hashlib
import html
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR'] = str(HERE / '.matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))

S, R, A, T = read('harness-summary.json'), read('selected-cells.json'), read('audit.json'), read('totals.json')
H, B, G = read('all-history-by-harness.json'), read('batch-ledgers.json'), read('dataset-summary.json')
LABEL = {r['harness']: r['harness_display'] for r in R}
ORDER = [s['group'] for s in S]
COLORS = {'accent': '#206488', 'neutral': '#626b72', 'muted': '#a8b2b8', 'warning': '#a76025'}
font = Path('C:/Windows/Fonts/msyh.ttc')
if font.exists():
    font_manager.fontManager.addfont(str(font))
    plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False, 'axes.unicode_minus': False, 'font.size': 10, 'figure.facecolor': 'white', 'axes.facecolor': 'white', 'svg.fonttype': 'path'})

def pct(x):
    return f'{100*x:.2f}%'

def md_table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(map(str, headers)) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |'] + ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows])

def save(fig, name):
    fig.savefig(HERE / (name + '.png'), dpi=190, bbox_inches='tight')
    fig.savefig(HERE / (name + '.svg'), bbox_inches='tight')
    plt.close(fig)

def charts():
    fig, axes = plt.subplots(2, 3, figsize=(16, 9.6), layout='constrained')
    panels = [
        ('严格整题准确率 ACC', 'strict_acc', 100, '通过题数 / 59（%）', 100),
        ('核心 API 用例通过率（微平均）', 'api_micro_acc', 100, '通过用例 / 803（%）', 100),
        ('新版 reward / 冻结满分', 'reward_weighted_rate', 100, 'reward 合计 / 138（%）', 100),
        ('完整 E2E 均值', 'mean_e2e_seconds', 1, '秒 / 题，含启动与评分', None),
        ('累计输入 + 输出 tokens', 'total_tokens', 1e-6, '百万 tokens / 59 题', None),
        ('模型用量目录价估算合计', 'list_cost_cny', 1, '人民币 / 59 题；非套餐账单', None),
    ]
    for ax, (title, key, mult, xlabel, upper) in zip(axes.flat, panels):
        values = [s[key] * mult for s in S]
        y = np.arange(6)
        ax.barh(y, values, height=.6, color=[COLORS['warning'] if s['group'].startswith('latte') else COLORS['accent'] for s in S])
        ax.set_yticks(y, [LABEL[s['group']] for s in S])
        ax.invert_yaxis()
        ax.set_title(title, loc='left', pad=12, fontweight='bold')
        ax.set_xlabel(xlabel)
        ax.set_ylabel('Harness')
        ax.grid(axis='x', alpha=.15)
        ax.set_axisbelow(True)
        ax.set_xlim(0, upper if upper else max(values) * 1.24)
        for i, v in enumerate(values):
            ax.text(v + (upper or max(values)) * .015, i, f'{v:.2f}' if mult == 100 else f'{v:.1f}', va='center', fontsize=9)
    fig.suptitle('Qwen3.8-Max 关闭推理 · Upstream59 v2.1.0 · 六套 Harness\n每套固定 59 格，基础设施补跑按最新授权选用，全部异常仍保留', fontsize=16, fontweight='bold')
    fig.supxlabel('来源：354 格选定评分、Harbor started_at→finished_at、逐请求 gateway usage；2026-11-26。LATTE 多数提前空规划退出，短耗时不代表解题效率高。', fontsize=9)
    save(fig, 'overview')

    tasks = sorted({r['task_id'] for r in R}, key=lambda t: (['C20','MS10','MP25','N4'].index(next(r['task_group'] for r in R if r['task_id'] == t)), t))
    lookup = {(r['harness'], r['task_id']): r for r in R}
    mat = np.array([[lookup[h,t]['normalized_reward'] for h in ORDER] for t in tasks])
    fig, ax = plt.subplots(figsize=(10, 19), layout='constrained')
    im = ax.imshow(mat, vmin=0, vmax=1, cmap='Blues', aspect='auto')
    ax.set_xticks(range(6), [LABEL[h] for h in ORDER], rotation=15, ha='right')
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position('top')
    ax.set_xlabel('Harness；单格底色 = 新版 reward / 该题冻结满分', labelpad=14)
    ax.set_ylabel('任务 ID（C20 / MS10 / MP25 / N4）')
    ax.set_yticks(range(len(tasks)), tasks)
    for i,t in enumerate(tasks):
        for j,h in enumerate(ORDER):
            r = lookup[h,t]
            label = f"{r['api_passed']}/{r['api_total']}" + (' S' if r['strict_pass'] else ' I' if not r['integrity_ok'] else '')
            ax.text(j, i, label, ha='center', va='center', fontsize=7.7, color='white' if mat[i,j] > .62 else '#25313a')
    for y in [19.5, 29.5, 54.5]:
        ax.axhline(y, color='#7d898f', linewidth=1)
    cb = fig.colorbar(im, ax=ax, fraction=.04, pad=.025)
    cb.set_label('新版 reward / 冻结满分（0–1）')
    fig.suptitle('59 题 × 6 Harness 完整结果矩阵\n格中文字为核心 API 通过数 / 冻结总数；S=严格通过，I=完整性失败', fontsize=14, fontweight='bold')
    save(fig, 'task-matrix')

def report():
    q = {s['group']: s for s in S}
    quality = md_table(['Harness', '严格 ACC', '核心 API 微平均', 'API 任务宏平均', 'reward 合计 / 138', 'reward 达成率', '完整性失败'], [[LABEL[s['group']], f"{s['strict_passed']}/59 · {pct(s['strict_acc'])}", f"{s['api_passed']}/803 · {pct(s['api_micro_acc'])}", pct(s['api_macro_acc']), f"{float(s['reward_sum']):.6f} / 138", pct(s['reward_weighted_rate']), s['integrity_failed_trials']] for s in S])
    timing = md_table(['Harness', '完整 E2E 均值（秒）', 'E2E 中位数 / P95（秒）', 'Agent 均值（秒）', '评分均值（秒）', '输入 / 输出（M tokens）', '输入缓存命中率', '目录价合计 / 均题（CNY）'], [[LABEL[s['group']], f"{s['mean_e2e_seconds']:.1f}", f"{s['median_e2e_seconds']:.1f} / {s['p95_e2e_seconds']:.1f}", f"{s['mean_agent_seconds']:.1f}", f"{s['mean_verifier_seconds']:.1f}", f"{s['input_tokens']/1e6:.3f} / {s['output_tokens']/1e6:.3f}", pct(s['input_cache_hit_rate']), f"{s['list_cost_cny']:.2f} / {s['mean_list_cost_cny']:.2f}"] for s in S])
    subsets = md_table(['Harness', 'C20 · ACC / API / reward', 'MS10 · ACC / API / reward', 'MP25 · ACC / API / reward', 'N4 · ACC / API / reward'], [[LABEL[h]] + [next(f"{g['strict_passed']}/{g['trials']} · {pct(g['api_micro_acc'])} · {float(g['reward_sum']):.4f}/{g['max_reward_sum']}" for g in G if g['group'] == h+':'+k) for k in ['C20','MS10','MP25','N4']] for h in ORDER])
    history = md_table(['Harness', '实际发过请求的 attempt', '其中旧付费 attempt', '发送 / 结算 / 未知请求', '全部已知用量目录价（CNY）'], [[LABEL[h['harness']], h['paid_attempts'], h['superseded_paid_attempts'], f"{h['requests_sent']}/{h['requests_settled']}/{h['requests_unknown']}", f"{h['list_cost_cny_known_usage']:.2f}"] for h in H])
    batches = md_table(['批次', '登记题位', '付费 attempt', '实际发送 / 结算 / 未知', '已知用量目录价（CNY）'], [[b['source'], b['registered_scope'], b['paid_attempts'], f"{b['sent']}/{b['settled']}/{b['unknown']}", f"{b['list_cost_cny']:.6f}"] for b in B])
    invalid = md_table(['Harness', '完整性失败的任务'], [[LABEL[h], '、'.join(r['task_id'] for r in R if r['harness'] == h and not r['integrity_ok'])] for h in ORDER if any(r['harness'] == h and not r['integrity_ok'] for r in R)])
    caprows = md_table(['终态', '数量', '任务'], [
        ['累计 token 闸门 ≥2M', 15, 'Codex C058；DSH C058；Nanobot C007、MP02、MP03、MP04、MP07、MP15、MP16、MP18、MP19、MP20、MP22、MP23、N22'],
        ['原生上下文超限', 1, 'Nanobot C058（本地估计 190988 / 190784）'],
        ['LATTE 五轮空规划', 56, '未产生有效 discover_task，原生退出及评分保留'],
        ['LATTE 100 轮仍未完成', 2, 'C068、C077'],
        ['LATTE 正常退出且有部分分', 1, 'C031：API 7/9、登记检查 11/13、reward 0.846154 / 2'],
    ])
    native = md_table(['Harness', '有原生子身份的题位', '观测子 ID 合计', '限定'], [[LABEL[s['group']], f"{s['observed_trials_with_children']}/59" if s['all_trials_have_native_child_count'] else '统一子身份计数字段未知', s['observed_child_id_count'] if s['all_trials_have_native_child_count'] else '未知', '会话身份审计；不能据此认定并行收益' if s['all_trials_have_native_child_count'] else '另有 LATTE 角色/任务事件，不能把缺失字段填成零'] for s in S])
    tasks = sorted({r['task_id'] for r in R}, key=lambda t: (['C20','MS10','MP25','N4'].index(next(r['task_group'] for r in R if r['task_id']==t)), t))
    lookup = {(r['harness'],r['task_id']):r for r in R}
    matrix = md_table(['任务']+[LABEL[h] for h in ORDER], [[t]+[f"{lookup[h,t]['api_passed']}/{lookup[h,t]['api_total']} · {float(lookup[h,t]['reward']):.3f}" + (' S' if lookup[h,t]['strict_pass'] else ' I' if not lookup[h,t]['integrity_ok'] else '') for h in ORDER] for t in tasks])
    lang, codex, nano = q['langgraph'], q['codex'], q['nanobot']
    cost_extra = A['all_history_list_cost_cny_known_usage'] - T['list_cost_cny']
    text = f'''# Qwen3.8-Max 关闭推理：59 题 × 6 Harness 完整结果报告

本报告汇总 **Upstream59 v2.1.0 的 354 个逻辑题位**，包括本次已授权基础设施补跑后的最终选用结果。模型为 `qwen3.8-max`，实际请求 `enable_thinking=false`；LATTE 使用 **planning-adapted 适配版**。这里的“跑完”指每个题位都有可审计评分及用量，并不表示每题都正常交付或全部通过。

本轮登记 **`forced_delegation=false`，不额外强制创建子 Agent**；各 Harness 使用其登记的原生运行路径。表中的“原主批”指同一轮 Qwen 主批，未混入其他模型的历史成绩。

全部运行已结束，最早付费试次于北京时间 **11 月 26 日 11:58:57** 启动，最后补跑于 **17:08:21** 结束；两者之间约 **5 小时 9 分钟**，包含排队、排空、离线修复和补跑间隔。报告统计快照：{A['at']}。本次只进行离线汇总，没有发起模型请求、重跑或上传 GitHub。

## 先看结论

- **整题成功率**：Codex、LangGraph、Nanobot 并列 **28/59＝47.46%**，DSH **27/59＝45.76%**，OpenCode **23/59＝38.98%**；LATTE 为 **0/59**。
- **部分功能与 reward**：LangGraph 的 API 微平均 **86.05%**、reward **89.406568/138** 均为本轮最高。最高 API 通过率并不等于更多整题通过。
- **时间与消耗**：Codex 的完整 E2E 均值为 **217.7 秒**，LangGraph 为 **440.4 秒**。相对 Codex，LangGraph 的 API 通过率高 **{100*(lang['api_micro_acc']-codex['api_micro_acc']):.2f} 个百分点**，E2E 约 **{lang['mean_e2e_seconds']/codex['mean_e2e_seconds']:.2f} 倍**、目录价约 **{lang['list_cost_cny']/codex['list_cost_cny']:.2f} 倍**；整题通过数相同。这是当前配置的描述性比较，不能单独归因为多 Agent。
- **LATTE 的短时间不能解释为高效率**：59 格中 **56 格五轮空规划、2 格 100 轮未完成**，只有 C031 正常退出并取得部分分；早退使平均 E2E 和 tokens 很低。它不是 59 道题都完成后零通过的对照。
- **费用不是账单**：选定 354 格的目录价估算为 **¥{T['list_cost_cny']:,.2f}**；包括所有旧付费 attempt 的已知用量目录价为 **¥{A['all_history_list_cost_cny_known_usage']:,.2f}**。实际 Token Plan 扣费、剩余额度和一笔历史 429 的用量均未知。

![六套 Harness 的质量、时间、tokens 与目录价比较](overview.png)

## 一、质量指标：ACC、API 和新版 reward

{quality}

六套都固定按 **59 格**统计整题 ACC，没有删除零分、超限或完整性失败题。每套的核心 API 冻结总数均为 **803**，登记核心检查总数均为 **1217**。API 微平均按全部用例汇总，宏平均先算每题通过率再对 59 题等权平均，二者回答的问题不同。

本轮全部 354 格都有原始评分；其中 **11 格 integrity_ok=false**，reward 按规则为 0，保留在分母中。它们不因为进程正常退出就被称为有效交付。

**reward 使用工作区当前默认 `delivery-bonus-50-v1`，354 格均已调用 `scoring/workspace_reward.py` 复算，全部与原分一致：**

`reward = I × W × (0.5 × K/N + 0.5 × S)`

- `I`：提交完整性；失败为 0。
- `W`：本版冻结的 reward 难度权重，M=2、H=3。
- `K/N`：冻结登记 A/B/D/P 核心检查通过数 / 总数，含业务转换、接口独立运行、产物和公开检查；分母不会因失败减少。
- `S`：严格通过，完整性、公开检查及全部登记核心检查均通过才为 1。
- 每题 Decimal 四舍五入到六位后求和；**不能把 API 比率直接代入 K/N**，也不能使用旧线性 reward。

每套 59 题的冻结 reward 难度为 **39M＋20H**，满分 **138**；独立实测难度标签为 **20M＋39H**。两种标签用途不同，不能用实测难度反推 reward 权重。表中 reward 达成率是 `Σreward/ΣW`；逐题归一化后等权的宏平均也已导出。

### 为什么三套 ACC 恰好相同

47.46% 是 **28/59**，不是三套通过了相同的题。Codex 与 LangGraph 共同严格通过20题，双方各有8道独有通过题；Codex 与 Nanobot 共同通过22题，各有6道不同。比如 Codex 通过了 C007 而 LangGraph 没有，LangGraph 通过了 C033/C055 而 Codex 没有。Codex 与 DSH 共同通过22题，Codex另有6题、DSH另有5题通过。

本轮59题每多通过一道，ACC增加约 **1.69个百分点**；严格通过是整题0/1，接近满分与只过少量检查都计为未严格通过，部分功能差异需要看API和reward。三套API微平均分别为81.07%、86.05%、82.69%，并不相同。当前每格一次有效运行，不能把通过数量并列当作重复结果、能力相等或已证明统计等效。

## 二、完整 E2E、tokens、缓存和成本

{timing}

完整 E2E 统一取 **Harbor `finished_at − started_at`**，包含环境启动、Agent 安装/执行、阶段切换和正式 verifier 评分；不包含试次启动前的队列等待和事后审计。Agent 与评分各阶段取自己的实际起止时间。表中的 P95 采用排序后线性插值。所有 354 格都有完整时间，不以 Agent 时间替代 E2E，不将父子执行时长相加冒充墙钟。

选定结果合计：输入 **{T['input_tokens']:,}**、输出 **{T['output_tokens']:,}**，总计 **{T['total_tokens']:,} tokens**；输入缓存命中 **{T['cache_tokens']:,} tokens**，token 加权命中率 **{pct(T['input_cache_hit_rate'])}**。缓存是输入的一部分，不能再加一次。数据使用供应商返回的 gateway usage，避免 DSH 原生日志“未缓存输入”和其他 Harness“全部输入”口径不同导致错算。

**目录价口径固定为本批登记的输入 ¥12/百万、输出 ¥36/百万：**

`目录价比较额 = 总输入 tokens × 12/1e6 + 输出 tokens × 36/1e6`

该比较额**没有应用缓存折扣**，也没有取得 Token Plan 账单、额度兑换或实际扣费数据。因此，它只是本批冻结的目录价比较值，不是现金支出，不是按 DeepSeek 谷价估算；也不应拿它推算套餐还剩多少钱。可识别缓存命中，但不能据此编造实际缓存计费。

全矩阵平均 E2E 为 **{T['mean_e2e_seconds']:.1f} 秒/格**，试次 E2E 之和约 **{T['sum_e2e_seconds']/3600:.2f} trial-hours**；后者是串行等价工作量，**不是实际批次历时**。六 Harness 合计严格通过 **134/354**，API **3305/4818**，reward **429.880109/828**；这些跨 Harness 总数仅供完整性汇总，不替代各 Harness 比较。

## 三、四类任务分组

任务构成为 C20、MS10、MP25、N4；先跑修订 C/MS30，再跑 MP/N29。每格依次为“严格通过数 / 题数 · API 微平均 · reward 合计 / 该组满分”。

{subsets}

分组 API 分母依次为 C20=181、MS10=101、MP25=482、N4=39；满分依次为 50、30、50、8。分母来自该组冻结用例数量，不能把不同任务组的百分比直接相加。

## 四、最终选用与全部历史消耗分开

最终每个任务×Harness 只选一个结果：**原主批 317 格＋OpenCode Git 修复 7 格＋LATTE 接口修复 27 格＋LATTE 服务恢复 3 格＝354 格**。选择按明确授权的最新基础设施恢复版本，**不取最高分**；原低分、旧异常和原账本均未覆盖。

例如 LATTE MS02 的旧 R2 产物曾获 **3/3**，但实际请求出现 429、用量未知；新 R3 是已授权恢复，五轮空规划获 **0/3**。主表使用 R3 的 0 分，旧高分只留在历史审计，不能择优放回主表。

{history}

共 **394 条 attempt 身份**：**387 条实际发过模型请求**、7 条发送前隔离占位。最终选定 354 条，另有 **33 条旧付费 attempt** 保留。它们的已知额外目录价约 **¥{cost_extra:.2f}**；不能把这部分运行消耗从实际实验投入里抹去。

{batches}

最终选定请求 **14486/14486 结算、未知 0**；全部历史请求 **15630 发出 / 15629 结算 / 未知 1**。未知的是 LATTE R2 **MS02** 的真实 HTTP429 请求 `b1169973b6a9499a8f1fb4a347e5d5fe`。它实际发出但无 usage，**不是发送前拦截**，未知用量和未知费用不填 0，也不会因为新重跑结算而消失。所有历史已结算 **15629 请求**均核验模型和 `enable_thinking=false`。

## 五、异常与比较限制

{caprows}

以上终态在主表完整保留；达到累计 2M token 闸门的 15 格是登记资源限制，不能叫作供应商失败或已触发循环检测。循环保护本次没有可据以声明触发的事件。Nanobot C058 是独立的原生上下文限制。LATTE 56 个空规划及两个轮数上限同样不是已证明的供应商故障，不为提升分数继续补跑。

### LATTE 为什么几乎没有进入有效交付

原生trace显示，主要瓶颈在“探索代码→登记任务→进入协作执行”的入口。当前配置最多允许5次规划模型回复；56题到上限时没有被接受的 `discover_task` 任务记录，运行时遂退出。这些题没有获得与其他Harness类似的长时间实现/验证机会。

例如修复后的 **C007**：第1轮跑公开检查，第2至4轮读公开检查、组件框架、实现和样例；第5轮仍在说“再读预期输出，然后生成任务”，接着读取4个文件，随后 `planning_phase_end` 记录 `tasks_discovered=0`、`turns=5`、`reason=max_turns`。补跑 **MS02** 也把5轮全部用于跑检查和阅读13个文件，任务数仍为0。旧 **MP01** 则出现试图运行 `script.py/explore.py` 的探索动作，同样耗尽规划轮数。

对照 **C031**：前4轮探索，第5轮生成3个有效 `discover_task`，运行时实际接受并进入执行，最终API7/9。这证明本地协议并非对Qwen完全不可用，也不能把所有空规划归因于XML解析坏了。另一方面，C068/C077进入执行后100轮仍未完成，说明规划入口不是唯一质量问题。

因此，目前支持的机制解释是 **Qwen关闭推理下持续探索的行为与LATTE五轮规划上限相冲突**。它不能证明“多给几轮必然通过”，也不是随机供应商报错的证据。应将本轮解释为登记配置下的结果；若要判断LATTE充分执行后的能力，需要另做固定题面/模型的规划轮数或提示兼容性对照。统一累计token上限不意味着各Harness的原生阶段轮数上限相同。本次只离线核对，不新增付费试次或修改旧配置。

完整性失败单列如下；这是原评分器的检查结论，本文不在没有额外证据时归因为模型、适配器或评分器错误。

{invalid}

原基础设施修复有两类，旧证据均保留：

1. **OpenCode 七格 EPIPE**：离线证实工作区没有 Git 元数据而运行时强制使用 Git，`git check-ignore` 先退出，造成管道关闭；以 `qwen-opencode-git-bootstrap/1.0.0` 初始化工作区 Git 元数据后七格独立补跑均完成，无 EPIPE。没有改题目、评分器、模型、CLI 权限或委派提示。
2. **LATTE 修订 30 题入口错配**：原适配器硬编码旧 `README.md/check.py`，新版提供 `TASK.md/public_check.py`；`qwen-latte-workspace-interface/1.0.0` 按实际布局绑定，旧 29 题保持等价。修复批随后 MS02 遇真实上游 429，并连带取消 C055/MS30；三格各自新 attempt 恢复后均完整结算。429 单凭现有记录不能进一步断定是现金余额不足还是具体限流配额。

**资源条件不是全部一致**：原主批及 LATTE R2 最多 6 Harbor 并发，共享 HTTP4；MS02 R3 单试次，C055/MS30 R4 双试次；OpenCode 的修复七格也另批调度。E2E 是各自实际测得值，环境存在共享资源竞争，不能把差异全归为 Harness 算法或修复收益。

本批没有总费用上限，但有统一的 **每试次累计观测输入＋输出 2M tokens** 门禁、通常每请求输出 32768（OpenCode 原生 8192）、六个相同轮保护；LATTE 保留规划 5 轮、执行 100 轮、3 队友配置。数据支持这些登记条件下的一次矩阵观察，不是无限预算能力排名，也不是单/多 Agent 因果消融。

## 六、原生子 Agent 身份观测补充

{native}

DSH 在 **MS29** 观测到 2 个子 ID；OpenCode 在 **C033、MP15** 各 1 个；LangGraph 沿用其工作流原生子身份定义。创建身份与有独立模型工作、结果回传、父接收和真实并行是不同证据层，本文没有把身份数量直接换算为并行收益。LATTE 的统一计数字段在最终选定证书中缺失，保留为未知，不按 0 解释。

## 七、完整逐题矩阵

![59 题完整矩阵：API 分子/分母及归一化 reward](task-matrix.png)

下表每格为 **“API 通过数/总数 · 新版 reward”**，`S` 为严格通过，`I` 为完整性失败。逐格的 E2E、输入/输出/缓存、目录价、源批次、原结果路径和终态见 CSV 或交互视图，均覆盖 354 格。

{matrix}

## 八、交付物、来源与复算

- [可筛选交互报告](dashboard.html)：筛选 Harness、任务组、任务 ID，查看逐格 E2E、tokens、目录价与异常。
- [逐格 CSV](selected-cells.csv) / [逐格 JSON](selected-cells.json)：最终选定 354 格。
- [Harness 汇总 CSV](harness-summary.csv) / [分数据集 CSV](dataset-summary.csv) / [分阶段 CSV](stage-summary.csv)。
- [全部历史 attempt CSV](all-attempts.csv) / [历史消耗汇总 CSV](all-history-by-harness.csv) / [批次账本 CSV](batch-ledgers.csv)。
- [异常清单 CSV](selected-anomalies.csv) / [核验回执 audit.json](audit.json)。
- [总览 PNG](overview.png) / [总览 SVG](overview.svg) / [逐题矩阵 PNG](task-matrix.png) / [逐题矩阵 SVG](task-matrix.svg)。
- [离线聚合脚本](aggregate_results.py) / [图表和报告生成脚本](build_report.py)。脚本不含凭据，不发送模型请求。
- [软件版本记录](software-versions.json) / [报告与筛选验收回执](artifact-verification.json)。

复算命令（从项目根目录执行）：

```powershell
wsl.exe --exec local-artifacts://wsl-home/.local/share/uv/tools/harbor/bin/python -B local-artifacts://project/outputs/qwen59-final-report-20261126-v1/aggregate_results.py
python outputs/qwen59-final-report-20261126-v1/build_report.py
```

权威选定证书：`outputs/qwen-latte-workspace-audit-20261126/corrected-matrix-selection.json`，SHA256 **`{A['selection_sha256']}`**。

数据集 v2.1.0 归档 SHA256 **`{A['dataset_sha256']}`**；主登记 SHA256 **`{A['original_manifest_sha256']}`**；reward policy SHA256 **`{A['reward_policy_sha256']}`**。59 题题面与 release-registry 哈希均匹配原冻结登记，354 份离线评分回执与其绑定的 Harbor 原结果哈希已核对；逐题 reward 与冻结分母复算一致，354 格均验证有实际资源采样。

原评分 JSON 内仍有 `benchmark_version=2.0.0` 的历史内部标签；本批题库版本依据 **v2.1.0 归档、题面和登记哈希**确定。报告保留原标签，没有改写评分器或原始文件来掩盖它。

完整原件位于 WSL `local-artifacts://wsl-runs/` 下的五个批次（路径与哈希见 `audit.json`）；本目录是可共享指标与报告包，不是完整原生 trace 复制。所有旧分数、旧用量未知和异常终态保留。本批试次已全部结束，也没有因本次汇总新增重跑；不对其他会话的实验运行状态作结论。
'''
    (HERE / '报告.md').write_text(text, encoding='utf-8')

def dashboard():
    # Embedded data: works offline without fetching any source or credential.
    compact = [{k:r[k] for k in ['harness','harness_display','task_id','task_group','strict_pass','api_passed','api_total','reward','max_reward','e2e_seconds','agent_seconds','verifier_seconds','input_tokens','output_tokens','cache_tokens','input_cache_hit_rate','list_cost_cny','terminal_classification','integrity_ok','selected_source','trial_id']} for r in R]
    data = json.dumps({'summary':S,'rows':compact,'audit':{k:v for k,v in A.items() if k not in ['sources','unknown_requests']},'history':H}, ensure_ascii=False).replace('</','<\\/')
    svg = (HERE / 'overview.svg').read_text(encoding='utf-8')
    svg = svg[svg.index('<svg'):]
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Qwen3.8-Max · 59×6 完整报告</title>
<style>body{margin:0;background:#f7f9fa;color:#202e38;font:15px/1.65 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1500px;margin:auto;padding:30px}h1{font-size:26px;margin:0}h2{font-size:20px;margin-top:30px}p{max-width:1100px}small,.muted{color:#53616b}.notice{border-left:4px solid #a76025;padding:12px 18px;background:#fff8ed}.wrap{overflow:auto;background:white;border:1px solid #dce3e7}table{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap}th,td{padding:10px 12px;text-align:right;border-bottom:1px solid #e5eaed}th{position:sticky;top:0;background:#eef3f5}td:first-child,th:first-child{text-align:left}tr:hover{background:#f0f6f8}.controls{display:flex;gap:12px;flex-wrap:wrap;margin:15px 0}select,input{padding:8px 12px;font:inherit;border:1px solid #acbbc4;background:white;color:inherit}svg{max-width:100%;height:auto}a{color:#206488}.bad{color:#9b4823}.statline{display:flex;gap:40px;flex-wrap:wrap;padding:15px 0}.statline b{font-size:24px;display:block}.kpi{min-width:150px}</style>
<main><h1>Qwen3.8-Max 关闭推理 · 59 题 × 6 Harness</h1><p>Upstream59 v2.1.0 · 最新授权基础设施恢复后选定354格；每套固定59题。所有已结算请求均核对 <code>enable_thinking=false</code>。运行已结束。</p>
<div class="statline"><div class="kpi"><b>354 / 354</b>有评分与完整 E2E</div><div class="kpi"><b>134 / 354</b>严格整题通过</div><div class="kpi"><b>429.880109 / 828</b>新版 reward 合计</div><div class="kpi"><b>¥2,644.42</b>选定结果目录价，非账单</div></div>
<p class="notice">实际 Token Plan 扣费未知。全部历史已知用量目录价 ¥2,746.41，另有一笔旧 MS02 HTTP429 无 usage；选定354格未知0，历史未知1。LATTE 56次空规划、2次轮数未完成，短时间不代表高效率。11格完整性失败保留为0分。</p>
<h2>Harness 主表</h2><p>API=核心业务转换用例通过率；reward=50%严格通过＋50%冻结登记检查进度，按难度加权。E2E=Harbor整次实际起止时间。</p><div class="wrap"><table><thead><tr><th>Harness</th><th>严格 ACC</th><th>API 微平均</th><th>reward /138</th><th>E2E均值 秒</th><th>输入tokens</th><th>输出tokens</th><th>缓存命中率</th><th>目录价 CNY</th></tr></thead><tbody id="summary"></tbody></table></div>
__SVG__
<h2>完整逐格数据</h2><div class="controls"><select id="h"><option value="">全部Harness</option></select><select id="g"><option value="">全部任务组</option><option>C20</option><option>MS10</option><option>MP25</option><option>N4</option></select><input id="task" placeholder="输入任务ID，如 C058"><select id="status"><option value="">全部终态</option><option value="strict">严格通过</option><option value="anomaly">原生退出或完整性异常</option></select></div><p id="count" class="muted"></p>
<div class="wrap" style="max-height:640px"><table><thead><tr><th>Harness / 任务</th><th>严格</th><th>API</th><th>reward</th><th>E2E 秒</th><th>Agent 秒</th><th>评分 秒</th><th>总tokens</th><th>缓存</th><th>目录价 CNY</th><th>终态</th><th>来源</th></tr></thead><tbody id="rows"></tbody></table></div>
<h2>阅读完整报告与原始指标</h2><p><a href="报告.md">中文完整报告</a> · <a href="selected-cells.csv">354格CSV</a> · <a href="all-attempts.csv">全部394条attempt</a> · <a href="audit.json">核验回执</a> · <a href="task-matrix.png">59×6完整矩阵图</a></p><small>数据来源：原始 score-v2、冻结 release-registry、Harbor result.json、gateway逐请求usage、原生资源采样；2026-11-26。目录价按本批冻结输入12/百万、输出36/百万CNY，不应用缓存折扣。没有显著性或因果收益声明。</small></main>
<script>const D=__DATA__;const f=(x,d=1)=>Number(x).toLocaleString('zh-CN',{maximumFractionDigits:d,minimumFractionDigits:d});const pct=x=>f(x*100,2)+'%';const el=x=>document.getElementById(x);const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const cells=rs=>rs.map(v=>'<td>'+esc(v)+'</td>').join('');
el('summary').innerHTML=D.summary.map(s=>'<tr>'+cells([D.rows.find(r=>r.harness===s.group).harness_display,s.strict_passed+'/59 · '+pct(s.strict_acc),s.api_passed+'/803 · '+pct(s.api_micro_acc),f(s.reward_sum,6),f(s.mean_e2e_seconds),f(s.input_tokens,0),f(s.output_tokens,0),pct(s.input_cache_hit_rate),f(s.list_cost_cny,2)])+'</tr>').join('');
D.summary.forEach(s=>{const o=document.createElement('option');o.value=s.group;o.textContent=D.rows.find(r=>r.harness===s.group).harness_display;el('h').append(o)});
function draw(){const rs=D.rows.filter(r=>(!el('h').value||r.harness===el('h').value)&&(!el('g').value||r.task_group===el('g').value)&&r.task_id.toLowerCase().includes(el('task').value.toLowerCase())&&(!el('status').value||(el('status').value==='strict'?r.strict_pass:r.terminal_classification!=='normal_agent_exit'||!r.integrity_ok)));el('count').textContent='显示 '+rs.length+' / 354 格；筛选只改变显示，不改变主表统计分母。';el('rows').innerHTML=rs.map(r=>'<tr>'+cells([r.harness_display+' / '+r.task_id,r.strict_pass?'通过':r.integrity_ok?'未全过':'完整性失败',r.api_passed+'/'+r.api_total,f(r.reward,6)+'/'+r.max_reward,f(r.e2e_seconds),f(r.agent_seconds),f(r.verifier_seconds),f(r.input_tokens+r.output_tokens,0),pct(r.input_cache_hit_rate),f(r.list_cost_cny,3),r.terminal_classification,r.selected_source])+'</tr>').join('')};['h','g','task','status'].forEach(k=>el(k).addEventListener('input',draw));draw();</script></html>'''
    (HERE / 'dashboard.html').write_text(page.replace('__SVG__',svg).replace('__DATA__',data), encoding='utf-8')
    (HERE / 'canvas-data.json').write_text(json.dumps({'summary':S,'rows':compact}, ensure_ascii=False), encoding='utf-8')

if __name__ == '__main__':
    charts()
    report()
    dashboard()
    files = [p for p in HERE.iterdir() if p.is_file() and p.name != 'artifact-sha256.json']
    (HERE / 'artifact-sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'report':str(HERE/'报告.md'),'dashboard':str(HERE/'dashboard.html'),'artifacts':len(files)},ensure_ascii=False))
