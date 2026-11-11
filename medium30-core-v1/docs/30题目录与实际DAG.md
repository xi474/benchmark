# 30 题目录、核心范围与实际 DAG

这里使用实现后的 contract.bindings 画图，替代候选阶段的示意拓扑。图表示必须等待的业务文件依赖，省略静态输入到下游的重复引用边；完整绑定见逐题契约。不把验证器或重复工作项算成业务并行分支。

- [N01　嵌套模型的输入输出依赖矩阵](tasks/N01.md)：`reasoning4`，3 组件，实际 DAG 宽度 2。
- [N02　维度替换后的元数据隔离](tasks/N02.md)：`context8`，3 组件，实际 DAG 宽度 2。
- [N03　多继承测试标记的 MRO 汇合](tasks/N03.md)：`reasoning4`，3 组件，实际 DAG 宽度 2。
- [N04　跨 SQL 后端的 XOR 奇偶语义](tasks/N04.md)：`context8`，3 组件，实际 DAG 宽度 2。
- [N05　数据库时区到业务日期的转换](tasks/N05.md)：`multistage4`，3 组件，实际 DAG 宽度 2。
- [N06　查询组合中的无碰撞别名重写](tasks/N06.md)：`reasoning4`，3 组件，实际 DAG 宽度 1。
- [N07　嵌套分数表达式的解析与保真输出](tasks/N07.md)：`reasoning4`，3 组件，实际 DAG 宽度 1。
- [N08　测试日志等级的作用域恢复](tasks/N08.md)：`context8`，3 组件，实际 DAG 宽度 2。
- [N09　多方日历可用区间的最早交集](tasks/N09.md)：`multistage4`，4 组件，实际 DAG 宽度 3。
- [N10　有限置换群的同态验证](tasks/N10.md)：`reasoning4`，3 组件，实际 DAG 宽度 2。
- [N11　零块保形的分块矩阵连乘](tasks/N11.md)：`reasoning4`，3 组件，实际 DAG 宽度 1。
- [N12　关联条件下不重复的外键选项](tasks/N12.md)：`multistage4`，3 组件，实际 DAG 宽度 2。
- [N13　主题合并后的待审帖子归属](tasks/N13.md)：`context8`，3 组件，实际 DAG 宽度 2。
- [N14　批量有序集合的累加与结果回填](tasks/N14.md)：`multistage4`，3 组件，实际 DAG 宽度 1。
- [N15　内部符号链接的保真构建与受限解包](tasks/N15.md)：`linux2`，3 组件，实际 DAG 宽度 1。
- [N16　书目迁移中两种冲突策略](tasks/N16.md)：`multistage4`，3 组件，实际 DAG 宽度 2。
- [N17　模板配置依赖与最小更新集合](tasks/N17.md)：`reasoning4`，3 组件，实际 DAG 宽度 1。
- [N18　保持编码的 URL 数字修改](tasks/N18.md)：`context8`，3 组件，实际 DAG 宽度 1。
- [N19　读写路由与事务内可见性](tasks/N19.md)：`multistage4`，3 组件，实际 DAG 宽度 2。
- [N20　目录与 ZIP 包的资源预加载](tasks/N20.md)：`context8`，4 组件，实际 DAG 宽度 2。
- [N21　词义统计 SQL 的等价优化](tasks/N21.md)：`reasoning4`，4 组件，实际 DAG 宽度 2。
- [N22　Git 遗失对象恢复与彻底清理](tasks/N22.md)：`linux2`，3 组件，实际 DAG 宽度 1。
- [N23　损坏 WAL 的修复与数据合并](tasks/N23.md)：`linux2`，3 组件，实际 DAG 宽度 2。
- [N24　COBOL 定长交易文件的 Python 等价迁移](tasks/N24.md)：`linux2`，4 组件，实际 DAG 宽度 3。
- [N25　本地 Git 双分支自动部署](tasks/N25.md)：`linux2`，3 组件，实际 DAG 宽度 1。
- [N26　双 KL 约束的概率分布构造](tasks/N26.md)：`reasoning4`，3 组件，实际 DAG 宽度 1。
- [N27　租房收藏整理与固定窗口新房源通知](tasks/N27.md)：`multistage4`，3 组件，实际 DAG 宽度 2。
- [N28　定时回复与按唯一收件人采购](tasks/N28.md)：`multistage4`，3 组件，实际 DAG 宽度 2。
- [N29　群成员响应阈值触发的出行安排](tasks/N29.md)：`multistage4`，3 组件，实际 DAG 宽度 2。
- [N30　移动后附件的跨渠道收件人分流](tasks/N30.md)：`linux2`，3 组件，实际 DAG 宽度 2。