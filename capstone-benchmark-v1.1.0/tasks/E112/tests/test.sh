#!/bin/bash
set -u
mkdir -p /logs/verifier
python3 /tests/dataset/verifier/score.py --package /tests/dataset --task E112 --workspace /app --json-output /logs/verifier/score-v1.json --reward-output /logs/verifier/reward.txt
