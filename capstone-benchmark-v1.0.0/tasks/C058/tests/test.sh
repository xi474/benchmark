#!/bin/bash
set -u
TASK_TEST_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p /logs/verifier
python3 "$TASK_TEST_DIR/score.py" --workspace /app --registry "$TASK_TEST_DIR/registry.json" --cases "$TASK_TEST_DIR/cases.json" --json-output /logs/verifier/score-v1.json --reward-output /logs/verifier/reward.txt
