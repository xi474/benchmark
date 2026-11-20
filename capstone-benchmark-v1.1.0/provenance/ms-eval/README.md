# MS-Eval 十题来源与改编

十题均为公开上游改编。原题来自 LINs Lab 的 MS-Eval oracle166；下表按原题文件的固定提交链接逐题归属。每行的中、难档取自本题包在 Terminus 2 与 DeepSeek V4 Pro 普通模式下的五次严格验收。上游难度字段留空。MS02 出自 11 月 19 日首批改编，其余九题出自 11 月 20 日可委派题续选。各题的 JSON 收录冻结设计卡、上游文件指纹和五测定档。

[单独下载这十题、评分记录和复算脚本](https://github.com/xi474/benchmark/raw/refs/heads/release/capstone-benchmark-v1.1.0/MS-Eval中难题发布包.zip)

| 本库题号与题目 | 上游原题 | 保留的业务内容 | 改编中增加的要求 | 实测档与严格通过 |
|---|---|---|---|---|
| [MS02](MS02.json) · 文献综述主题分配与证据图更新 | [academic-literature-review](https://github.com/LINs-lab/MS-Eval/blob/4c1bbd3dc0d736623bba563e56cfd8666f85daac/data/oracle166/academic-literature-review.task.md) | 主题槽与稳定论文ID一一匹配，方法证据作为准入，保留既有知识图边，综述仅用最终论文。 | 不同主题争用相同证据源，引入先保瓶颈再保总质量的联合分配。 | [中 · 3/5](../../evidence/MS02/trials.json) |
| [MS11](MS11.json) · 匿名书店账户与学生成绩的关联区间 | [terminal-canvas-wc-excel-ppt-email](https://github.com/LINs-lab/MS-Eval/blob/4c1bbd3dc0d736623bba563e56cfd8666f85daac/data/oracle166/terminal-canvas-wc-excel-ppt-email.task.md) | 两门课全部已评分提交、学生与书店账户登记、所有订单状态、电子与相机品类、消费与成绩的 Pearson 方向。 | 将唯一登记映射扩展为按来源可撤回的多候选登记，求最优映射族上的相关方向范围和必要配对。 | [难 · 1/5](../../evidence/MS11/trials.json) |
| [MS12](MS12.json) · 午餐供应波动下的全周菜单承诺 | [terminal-howtocook-gform-excel-notion-email](https://github.com/LINs-lab/MS-Eval/blob/4c1bbd3dc0d736623bba563e56cfd8666f85daac/data/oracle166/terminal-howtocook-gform-excel-notion-email.task.md) | 饮食偏好、禁用配料、难度上限、相邻品类不同及面向全员的周菜单成本。 | 在可观察的交货情景树上合并前缀决策，联合求解群体公平、加权满意度与支出，并核对多解。 | [中 · 3/5](../../evidence/MS12/trials.json) |
| [MS14](MS14.json) · 共享故障域的可用性报告与持续恢复方案 | [fetch-notion-monitoring](https://github.com/LINs-lab/MS-Eval/blob/4c1bbd3dc0d736623bba563e56cfd8666f85daac/data/oracle166/fetch-notion-monitoring.task.md) | up/down/degraded 时间日志、按服务提取连续事故、恢复时刻或窗口末截断。 | 加入版本化观测、共享底层依赖与法定数服务规则；要求跨完整值班窗口持续恢复的全部包含极小方案。 | [难 · 0/5](../../evidence/MS14/trials.json) |
| [MS23](MS23.json) · 三个匿名反馈渠道的改进优先级 | [customer-satisfaction-analytics-framework](https://github.com/LINs-lab/MS-Eval/blob/4c1bbd3dc0d736623bba563e56cfd8666f85daac/data/oracle166/customer-satisfaction-analytics-framework.task.md) | 调查、商品评论、服务接触点的客户满意度汇总及改进方向判断。 | 将跨渠道失去逐人链接建模为保留全部两两投影的匿名整数表，核验净支持人数的完整识别范围。 | [中 · 3/5](../../evidence/MS23/trials.json) |
| [MS28](MS28.json) · 截止日辅导窗口的共同容量瓶颈 | [canvas-assignment-deadline-word-gcal](https://github.com/LINs-lab/MS-Eval/blob/4c1bbd3dc0d736623bba563e56cfd8666f85daac/data/oracle166/canvas-assignment-deadline-word-gcal.task.md) | 逐作业截止日、无截止日处理、提前七天的日历窗口、作业点数及统一教务报告。 | 把多个提醒窗口投射到共享辅导日历，求所需容量的精确倍数和达到瓶颈的全部集合之间的必要关系。 | [中 · 3/5](../../evidence/MS28/trials.json) |
| [MS29](MS29.json) · 三道工作坊菜品的合并采购与可执行备料 | [howtocook-workshop-materials](https://github.com/LINs-lab/MS-Eval/blob/4c1bbd3dc0d736623bba563e56cfd8666f85daac/data/oracle166/howtocook-workshop-materials.task.md) | 三道不同品类的容易菜、食材合并购物单、按实际可行顺序给出备料步骤。 | 按整包采购，允许共用副产物和有启动物料要求的循环工序，核对最低成本采购与实际可执行见证。 | [中 · 2/5](../../evidence/MS29/trials.json) |
| [MS30](MS30.json) · 金融素养工作坊的双向稳定分班 | [terminal-yf-canvas-excel-gcal-email](https://github.com/LINs-lab/MS-Eval/blob/4c1bbd3dc0d736623bba563e56cfd8666f85daac/data/oracle166/terminal-yf-canvas-excel-gcal-email.task.md) | 两门财务课每次提交百分比的等权分层、市场数据最新日和 30 天窗口、按绝对涨跌挑选案例、定向工作坊。 | 学生偏好与工作坊分层优先级可并列；以稳定性而非单边评分判断分班，并核对取消活动后的最大覆盖。 | [中 · 2/5](../../evidence/MS30/trials.json) |
| [MS41](MS41.json) · 推理方法综述中的自一致投票复核 | [arxiv-latex-reasoning-gsheet](https://github.com/LINs-lab/MS-Eval/blob/4c1bbd3dc0d736623bba563e56cfd8666f85daac/data/oracle166/arxiv-latex-reasoning-gsheet.task.md) | 保留原综述比较逐次作答与 self-consistency 等方法并形成统一比较表的目标；用给定的方法与试验资料代替外部检索。 | 从描述性文献对比扩展为准确评估合成方法状态图；处理未决循环、同题多票共享的潜在版本、提前决出胜负与正确条件下的总花费。数值并非上游论文报告的实验。 | [难 · 1/5](../../evidence/MS41/trials.json) |
| [MS42](MS42.json) · 跨年课程的可比考核与成绩变化 | [canvas-course-comparison-word](https://github.com/LINs-lab/MS-Eval/blob/4c1bbd3dc0d736623bba563e56cfd8666f85daac/data/oracle166/canvas-course-comparison-word.task.md) | 保留按开课代码共同前缀匹配两个秋季学期、排除空分数和以所有已评分提交计算均值的口径。 | 存在全校共享但有多解的标签字典，用两年的先修偏序约束考核对齐。统计真实配对集合，给出最优证据下整体均值之差的范围。 | [难 · 0/5](../../evidence/MS42/trials.json) |

MS42 的冻结评分为 0/5。仅把同一用例的小数成绩等价换算为四分之一分整数单位，四份提交转为通过，诊断结果为 4/5。另一份提交在核心对齐用例超时。 [查看五份提交的对照记录](../../evidence/MS42/replay/grade-units-control.json)

[上游 MIT 许可证](LICENSE) · [定档协议](protocol.json) · [运行环境](runtime.json)
