# Parallel20 semantic parallelism ON/OFF traces

Paired SemServe Runtime traces for the first ten Parallel20 task profiles, run on 2026-11-16. Both arms used DeepSeek V4 Pro with reasoning mode off.

- ON source run: `20261116-parallel20-profiles-current-first10-v1`
- OFF source run: `20261116-parallel20-profiles-current-off-first10-v1`
- Each JSONL file preserves the original Runtime trace bytes and event order.
- Score columns summarize post-run results. No hidden verifier inputs, scripts, or per-case diagnostics are included.
- `SHA256SUMS` covers all 30 traces. Paths are relative to this directory.

| Arm | Public passed | Strict passed | API passed | Reward |
| --- | ---: | ---: | ---: | ---: |
| ON | 10/10 | 8/10 | 109/113 | 17.50/20 |
| OFF | 5/10 | 3/10 | 48/113 | 7.25/20 |

| Task | ON trace | OFF trace | ON API | OFF API | ON reward | OFF reward |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| E112 | [JSONL](traces/on/E112/trace.jsonl) | [JSONL](traces/off/E112/trace.jsonl) | 11/12 | 0/12 | 0.8125 | 0 |
| F15 | [JSONL](traces/on/F15/trace.jsonl) | [JSONL](traces/off/F15/trace.jsonl) | 9/12 | 0/12 | 0.6875 | 0 |
| F18 | [JSONL](traces/on/F18/trace.jsonl) | [JSONL](traces/off/F18/trace.jsonl) | 12/12 | 0/12 | 2 | 0 |
| F20 | [JSONL](traces/on/F20/trace.jsonl) | [JSONL](traces/off/F20/trace.jsonl) | 12/12 | 12/12 | 2 | 2 |
| I06 | [JSONL](traces/on/I06/trace.jsonl) | [JSONL](traces/off/I06/trace.jsonl) | 12/12 | 12/12 | 2 | 2 |
| K54 | [JSONL](traces/on/K54/trace.jsonl) | [JSONL](traces/off/K54/trace.jsonl) | 12/12 | 7/12 | 2 | 0.5625 |
| K64 | [JSONL](traces/on/K64/trace.jsonl) | [JSONL](traces/off/K64/trace.jsonl) | 12/12 | 4/12 | 2 | 0.25 |
| L114 | [JSONL](traces/on/L114/trace.jsonl) | [JSONL](traces/off/L114/trace.jsonl) | 12/12 | 5/12 | 2 | 0.4375 |
| Q08 | [JSONL](traces/on/Q08/trace.jsonl) | [JSONL](traces/off/Q08/trace.jsonl) | 9/9 | 0/9 | 2 | 0 |
| Q20 | [JSONL](traces/on/Q20/trace.jsonl) | [JSONL](traces/off/Q20/trace.jsonl) | 8/8 | 8/8 | 2 | 2 |

## Thinking high, semantic parallelism OFF

This separate run used DeepSeek V4 Pro with thinking enabled and the provider's default high effort. Semantic parallelism was off.

The ten traces are the final files assembled in `20261116-parallel20-profiles-current-reasoning-off-first10-v2-final-resume`. The archive uses one final trace per task. K64 and L114 use the final retries after earlier interruptions.

Public and strict validation both passed on 10/10 tasks. API checks passed on 113/113 cases and reward was 20/20. These are post-run scores of the saved workspaces. The K64 and L114 traces also record a Runtime `task_failed` event.

| Task | Thinking high trace | API passed | Reward |
| --- | --- | ---: | ---: |
| E112 | [JSONL](traces/thinking-high-off/E112/trace.jsonl) | 12/12 | 2 |
| F15 | [JSONL](traces/thinking-high-off/F15/trace.jsonl) | 12/12 | 2 |
| F18 | [JSONL](traces/thinking-high-off/F18/trace.jsonl) | 12/12 | 2 |
| F20 | [JSONL](traces/thinking-high-off/F20/trace.jsonl) | 12/12 | 2 |
| I06 | [JSONL](traces/thinking-high-off/I06/trace.jsonl) | 12/12 | 2 |
| K54 | [JSONL](traces/thinking-high-off/K54/trace.jsonl) | 12/12 | 2 |
| K64 | [JSONL](traces/thinking-high-off/K64/trace.jsonl) | 12/12 | 2 |
| L114 | [JSONL](traces/thinking-high-off/L114/trace.jsonl) | 12/12 | 2 |
| Q08 | [JSONL](traces/thinking-high-off/Q08/trace.jsonl) | 9/9 | 2 |
| Q20 | [JSONL](traces/thinking-high-off/Q20/trace.jsonl) | 8/8 | 2 |
