# SemServe Agent-Parallelism 18-Entry Task Pack

## 最新六Harness对比汇报（2026-11-10）

[查看GLM low与V4 Pro普通模式的Core6＋Medium5图文报告](experiments/glm-v4pro-core6-medium5-2026-11-10/README.md)：六套正式baseline为Nanobot、OpenCode、Codex、DSH、LangGraph、LATTE planning-adapted；主对比132题位、推理/显式补充30题，共162份选定提交。包含13张图、逐题API/Strict/Reward、E2E、tokens、输入缓存、费用估算、异常标签及跨批次配置限制。采用独立冻结的50%交付奖评分迁移；此前八臂报告保留为历史，不混入当前六套范围。


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

## Medium26 extension v1

The [Medium26 add-on](medium26-extension-v1/README.md) adds 26 tasks with a medium design target, adapted from SWE-bench Verified, SWE-bench Pro, Terminal-Bench and GAIA2. It preserves the four suite styles: 9 multistage4, 7 reasoning4, 5 context8 and 5 linux2 tasks, using only the Python standard library.

See the [Chinese task catalogue and author DAGs](medium26-extension-v1/docs/26题中文目录与DAG.md), [current difficulty standard](medium26-extension-v1/docs/难度分级标准_v1.1.md), [validation report](medium26-extension-v1/review/交付与验收.md), and [Agent-only archive](medium26-extension-v1-agent.zip). Reference solutions, hidden probes and author diagrams are kept outside each initial workspace. Difficulty and parallel speedup remain uncalibrated by model experiments.

## Reward evaluation v2

[Evaluation v2](evaluation-v2/README.md) adds fixed-count partial credit without changing existing task inputs or requirements. Easy, medium and hard tasks have maximum rewards of 1, 2 and 3; each reward is the difficulty maximum multiplied by passed verifiers divided by the task's fixed verifier count. It retains existing checks, records all results, and gives zero for protected-file tampering. Original binary scores remain versioned separately.

See the [policy](evaluation-v2/policy.json), [fixed catalog](evaluation-v2/catalog.json), [offline five-task re-score](evaluation-v2/review/离线重评分.md), and [validation report](evaluation-v2/review/validation_report.json). Future Harbor runs should use the new external test adapter so fractional rewards are read directly instead of mapped from exit status.


## 运行结果（独立实验材料）

[查看V4 Pro普通模式 reward-v2 当前运行汇报](experiments/reward-v2-v4pro-2026-11-08/README.md)：2026-11-09按规格质量裁决，从八臂统一排除MP04、MP08、MP09、MP10、MP11、MP24，Medium26修订为Medium20；当前原14＋mixed16-v4的16＋Medium20，共八臂400个选定题位。API检查通过率、E2E、tokens、输入缓存、费用、资源及multi-agent指标已离线重算；旧448题位和LATTE四次独立补跑留档，原attempt及分数不覆盖。结果与分析只放在experiments目录；不要将该目录或作者验证材料挂载给被测Agent。不同Harness限额、适配条件与异常终态在报告中分别标注。
