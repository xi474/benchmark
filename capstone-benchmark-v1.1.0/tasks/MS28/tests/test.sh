#!/bin/bash
set -u
D="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p /logs/verifier
python3 "$D/score.py" --workspace /app --registry "$D/registry.json" --cases "$D/cases.json" --json-output /logs/verifier/score-v1.json --reward-output /logs/verifier/reward.txt
