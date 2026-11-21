# MS 家族严格通过率低（3/10）的根因分析（2026-11-21 18:05）

**现象**：统一账（重放后）MS 严格 3/10（30%），显著低于 MP 60%；A 类 68/101（67.3%）。

## 一、表层：失败项集中在 A 类，B/D 是下游

10 题失败项合计 **A 33 / B 9 / D 9 / P 1**。B（干净独立构建）与 D（CLI 重算）失败的题全部同时也是 A 部分失败的题——transform 本身错则构建/重算跟着错，B/D 不是独立根因。

| 题 | K/N | A | 失败项 |
|---|---|---|---|
| MS12/MS23/MS29 | 全过 | 全对 | 无（strict 的全部来源） |
| MS02 | 12/14 | 7/9 | A/ties、A/parallel-evidence |
| MS30 | 12/15 | 9/10 | 1 A + B2 + D2 |
| MS42 | 11/17 | 8/12 | 4 A（含 shared-labels×2）+ B2 + D2 |
| MS28 | 7/15 | 6/10 | 4 A（hidden-implication 等）+ 2B + 2D |
| MS41 | 8/16 | 5/11 | 6 A（two-profile-mix、two-state-cycle 等）+ B1 + D1 |
| MS14 | 4/15 | 3/10 | 7 A（shared-provider、clipped-windows 等）+ 2B + 2D |
| MS11 | 1/15 | 1/10 | 9 A（component-coupling、conflicting-registers、merge-and-split 等）+ 2B + 2D + P |

## 二、机制层：v2.1 模块化对 MS 是负迁移（与 C 家族方向相反）

退步三题的 v2.0 → v2.1 对照：

| 题 | v2.0（单文件） | v2.1（模块化 2+1） |
|---|---|---|
| MS02 | **14/14 全对、A 9/9（strict 3.0）** | 12/14、A 7/9（1.27） |
| MS11 | 14/15、A 9/10（差 1 项） | 1/15、A 1/10（崩坏） |
| MS14 | 12/15、A 9/10 | 4/15、A 3/10 |

**失败用例名直指跨组件耦合语义**：`component-coupling`、`shared-provider`、`shared-labels-1/2`、`conflicting-registers`、`two-profile-mix`、`merge-and-split`、`parallel-evidence`、`ties`——全部是**两个组件结果合并时的纠缠规则**。

## 三、结构证据：integration 层没有契约、没有检查器

组件契约各管一个数据投影（MS02：evidence_scores 管评分表、graph_facts 管图事实三元组），但 `work_units.json` 的 **integration 项只有 implementation/reads，没有 contract 字段**，也没有独立的 integration 检查器（focused_check 只能跑根级 public_check，公开样例仅 1 个）。耦合规则（平局、并行证据、共享标签、寄存器冲突）落在无契约的 `integration.py` 裸占位里，agent 只能靠 TASK.md 全文自行理解——而这正是 v2.0 单文件 agent 本来就做的事，现在还被切断了跨组件上下文。

MS02 实例：两个失败 A（`ties`、`parallel-evidence`）恰好都是 evidence_scores × graph_facts 的合并规则——integration 层职责。

## 四、结论与改进方向

MS-Eval 的业务规则是**纠缠的单一推理整体**（oracle166 的评分/图事实/日历规则互相关联），与 C 家族（SWE-bench/TB 的**可分数据投影**）相反：切分成"2 组件 + 无契约 integration"引入**接缝缺陷**——组件各自正确，合并在耦合规则上错。

补全今天的因果链：**任务结构决定并行，但切分方式必须与规则耦合度匹配**——C 的规则可分（模块化 +），MS 的规则纠缠（模块化 −，v2.0 单文件 4/10 strict 反而更高）。

改进选项：
- **a. integration 契约化**：把合并/平局/共享规则写进 integration 的 contract 字段 + 独立检查器（对称 J2-a 的第三块拼图）；
- **b. 耦合规则组件化**：跨组件规则做成第三个显式组件（有自己的 work.py + check）；
- **c. 形态回退**：MS 用 v2.0 单文件形态（接受串行换正确率）。

## 五、产物

- 失败项分解：`ms_analysis.txt`；组件契约：`benchmark/tasks/MS{02,11,14}/environment/workspace/work_units.json`
