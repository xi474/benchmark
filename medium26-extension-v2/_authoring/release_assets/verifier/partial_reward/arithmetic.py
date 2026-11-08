from decimal import Decimal,ROUND_HALF_UP
def reward(passed,total,difficulty,policy,integrity=True):
    if type(passed) is not int or type(total) is not int or not 0<=passed<=total or total<=0:raise ValueError('invalid fixed verifier counts')
    maximum=Decimal(str(policy['difficulty_max_reward'][difficulty]))
    if not maximum.is_finite() or maximum<=0:raise ValueError('invalid difficulty reward')
    exact=maximum*Decimal(passed)/Decimal(total) if integrity else Decimal(0)
    rounded=exact.quantize(Decimal(1).scaleb(-policy['decimal_places']),rounding=ROUND_HALF_UP)
    return dict(reward=float(rounded),max_reward=float(maximum),passed_verifiers=passed,total_verifiers=total,pass_ratio=passed/total,integrity_ok=bool(integrity),all_checks_passed=bool(integrity and passed==total))
