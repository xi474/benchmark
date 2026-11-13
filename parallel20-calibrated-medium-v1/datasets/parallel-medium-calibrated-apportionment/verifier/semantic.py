from fractions import Fraction
import json


def normalize(ident, value):
    if not isinstance(value, dict) or not isinstance(value.get("appeals"), dict):
        return value
    results = {}
    for appeal, result in value["appeals"].items():
        if not isinstance(result, dict) or "loss" not in result:
            results[appeal] = result
            continue
        pair = result["loss"]
        if not isinstance(pair, list) or len(pair) != 2 or not all(type(v) is int for v in pair) or pair[1] <= 0:
            raise ValueError("positive-denominator integer fraction required")
        f = Fraction(*pair)
        results[appeal] = {**result, "loss": [f.numerator, f.denominator]}
    return {**value, "appeals": results}


def check_value(ident, name, actual, wanted, context=None):
    try:
        return json.dumps(normalize(ident, actual), sort_keys=True) == json.dumps(normalize(ident, wanted), sort_keys=True)
    except (TypeError, ValueError):
        return False
