#!/bin/bash
set -u
mkdir -p /logs/verifier
python3 /tests/evaluation-v2/score.py --benchmark-root /tests/benchmark --task hard/batch_scheduler_transition_spec_v4 --workspace /app --json-output /logs/verifier/score-v2.json --reward-output /logs/verifier/reward.txt
exit "$?"
