"""Workspace default for xi474 task reward. Inputs are frozen counts from one attempt."""
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

POLICY_FILE = Path(__file__).with_name("reward-policy-v1.0.json")
POLICY_SHA256 = "7cf383ca7b92cdc0cbfc555e8193391fa0da198b21cdda5a915fea34f02483b8"
policy_bytes = POLICY_FILE.read_bytes()
if hashlib.sha256(policy_bytes).hexdigest() != POLICY_SHA256:
    raise ValueError("Reward policy differs from the adopted xi474 policy. Check the scoring revision.")
POLICY = json.loads(policy_bytes)
SCORING_REVISION = POLICY["scoring_revision"]


def task_reward(*, difficulty, passed, total, strict_pass, integrity_ok):
    """Return a six-decimal Decimal, or None when scoring evidence is unavailable.

    passed and total count registered A, B, D and P checks (P once).
    Missing individual outcomes count against the fixed total. A missing
    scoring receipt is represented by unknown inputs, not as a failed check.
    External benchmark users must document their proxies separately.
    """
    if difficulty not in POLICY["difficulty_max_reward"]:
        raise ValueError("Use the frozen release difficulty E, M or H.")
    for flag in (strict_pass, integrity_ok):
        if flag is not None and type(flag) is not bool:
            raise TypeError("strict_pass and integrity_ok must be bool or None")
    if integrity_ok is False:
        return Decimal("0.000000")
    if None in (integrity_ok, strict_pass, passed, total):
        return None
    if type(passed) is not int or type(total) is not int or not 0 <= passed <= total or total <= 0:
        raise ValueError("Expected integer counts 0 <= passed <= total and a positive frozen total.")
    if strict_pass != (passed == total):
        raise ValueError("Strict pass disagrees with the complete frozen core checks and integrity evidence.")
    weight = POLICY["difficulty_max_reward"][difficulty]
    progress = Decimal(str(POLICY["progress_fraction"]))
    delivery = Decimal(str(POLICY["completion_bonus_fraction"]))
    value = weight * (progress * passed + delivery * int(strict_pass) * total) / total
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
