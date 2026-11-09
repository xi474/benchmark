# SemServe Agent-Parallelism 18-Entry Task Pack

## 统一评分标准：50%完整交付奖励

采用 **50%核心验收完成分＋50%整题严格通过奖励**，单题上限按发布前冻结的E/M/H权重1/2/3确定。公开通过、**核心转换用例通过率**（原API acc）与严格通过分别报告。

**[正式评分规范 v1.0](docs/scoring/统一评分标准_v1.0.md)** · [机器可读规则](docs/scoring/reward-policy-v1.0.json) · [合成计分示例](docs/scoring/examples-v1.0.json)

规范已采纳；已有数据包的旧评分器尚未自动迁移。实施须独立冻结评分版本及检查清单；任务内容与历史成绩保留。仅对旧记录重算50%权重，不等同于通过新增严格验收。

## 数据集入口：改编26题已同步到 main

**[独立六题v3五次复测分档汇总](results/adapted6-core-v3-terminus2-v4pro-five-20261109/README.md)**：30/30次完成，核心成功14/30；易1题、中3题、难2题。仅公开脱敏汇总，通用稳健性单独记录。

- **[独立六题核心版 v3（本轮复测入口）](adapted6-core-v3/README.md)**：核心业务完成与通用稳健性分开评分；[六题目录与DAG](adapted6-core-v3/docs/六题中文目录与DAG.md)、[新评分与难度规则](adapted6-core-v3/docs/难度分级标准_v3.md)、[下载Agent包](adapted6-core-v3-agent.zip)、[下载完整包](adapted6-core-v3-full.zip)。这是原MP04/08/09/10/11/24的独立新版本；原26题包及v2成绩保留，不新增题型数量。

- **[改编26题 v2：20题原版 + 6题修订版](medium26-extension-v2/README.md)**：26题统一入口，共93个组件；[直接浏览任务](medium26-extension-v2/tasks/)、[26题中文目录和DAG](medium26-extension-v2/docs/26题中文目录与DAG.md)、[下载Agent任务包](medium26-extension-v2-agent.zip)、[下载完整包](medium26-extension-v2-full.zip)。
- [六题独立修订集](medium6-specfix-v2/README.md)：MP04、MP08、MP09、MP10、MP11、MP24；[下载六题Agent包](medium6-specfix-v2-agent.zip)。这是上述26题的子集，便于单独复测。
- [原始14题](tasks/)：原始suite共18个入口、14个不同题目。
- [Mixed16 精确规格 v4](mixed16-precise-spec-v4/README.md)：16道独立扩展题。
- [同事新增 Long Parallel10](long-parallel10-10r-20261104/README.md)：独立的10题、30组件任务集。

原14题 + Mixed16的16题 + 本改编26题，共56道不同题目；六题独立包作为版本子集统计，同事新增10题另行统计。26题中的20题TASK/初始workspace与v1逐字节一致，6题采用已发布修订版，见[逐题组成核对](medium26-extension-v2/review/distribution_composition.json)。

26题均附来源与原始难度标注、作者DAG、独立正式verifier和小数reward评分器。使用时只向Agent提供单题TASK.md与初始workspace；作者材料和verifier放在Agent工作区外。Medium26/M保留历史设计目标，实测难度按对应版本的baseline另行记录。此前这批材料位于工作分支，本入口于2026-11-09同步到main。


This package contains the original task prompts and initial workspaces used by
the Retest18 experiment. It is intended for evaluating whether an agent harness
can discover dependency structure and parallel opportunities during execution.

## Dataset shape

- 18 benchmark entries across four suites: `multistage4`, `reasoning4`,
  `context8`, and `linux2`.
- 14 unique task names. Four workloads intentionally occur in both
  `multistage4` and `context8`, preserving the historical experimental suites.
- Every entry contains `TASK.md` and an untouched initial `workspace/`.

## No topology leakage

The package intentionally excludes experiment-side `case.json` files, planned
DAGs, frontier timing rules, expected classifier labels, traces, model outputs,
and execution results. A harness should give the model the task text and the
initial workspace only. Any dependencies or parallel opportunities must be
discovered online.

## Running an entry

1. Send `TASK.md` as the user request.
2. Mount or copy `workspace/` as the agent's working directory.
3. Let the harness execute the task without reading hidden experiment metadata.
4. When a root `check.py` exists, run `python check.py` after the agent finishes.

`manifest.json` records task counts and SHA-256 digests for reproducibility.

## Mixed16 extension (v3)

The separately versioned [Mixed16 v3 extension](mixed16-extension-v3/README.md)
adds 16 unique tasks: four each in the `multistage4`, `reasoning4`, `context8`,
and `linux2` styles. Its [manifest](mixed16-extension-v3/manifest.json) and
checksums are independent of the original 18-entry manifest at the repository root.

The extension combines file dependencies with constrained scheduling, stateful
recovery, compatibility checks, and graph algorithms. Author validation covers
all 16 reference solutions, 452 API cases, 82 rejected mutations, and 56 small
independent algorithm checks. These are correctness checks, not measured agent
performance results.

For an evaluation, provide only one task's `TASK.md` and initial `workspace/`.
Keep the extension's `_authoring/` and `verifier/` directories outside agent
mounts; they contain reference algorithms, hidden checks, and trusted hashes.
Local `check.py` is a smoke test; official scoring uses the external verifier.
Do not mount the whole repository as an agent workspace.

### Component DAG gallery

[Browse the DAGs for all 16 Mixed16 v3 tasks](mixed16-extension-v3/_authoring/dags/README.md).
Each task includes SVG/PNG diagrams, editable Mermaid source, and validated
dependency data. Diagrams are author-only metadata; keep them outside agent
mounts along with the rest of `_authoring/`.
