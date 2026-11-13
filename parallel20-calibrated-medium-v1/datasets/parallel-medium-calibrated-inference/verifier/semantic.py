from fractions import Fraction
import json


def normalize(ident, value, field=""):
    if isinstance(value, dict):
        return {k:normalize(ident,v,k) for k,v in value.items()}
    if isinstance(value, list):
        if ident=="S04" and field=="first_tests":
            return sorted(value)
        if ident=="S03":
            if len(value)==2 and all(type(v) is int for v in value):
                if value[1]<=0:
                    raise ValueError
                q=Fraction(*value)
                return [q.numerator,q.denominator]
            return [normalize(ident,v) for v in value]
    return value


def check_value(ident,name,actual,wanted,context=None):
    try:
        return json.dumps(normalize(ident,actual),sort_keys=True)==json.dumps(normalize(ident,wanted),sort_keys=True)
    except (TypeError,ValueError):
        return False
