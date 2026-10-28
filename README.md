# SemServe Agent-Parallelism 18-Entry Task Pack

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
