"""Comparison for JSON reports: keyed collections and equivalent fractions."""
from fractions import Fraction
import json

UNORDERED = {
    'Q01': {'models', 'events', 'retained', 'excluded'},
    'Q02': {'results'},
    'Q03': set(),
    'Q04': {'runs'},
    'Q05': {'queries', 'coefficients', 'min_assignment', 'max_assignment'},
    'Q06': {'levels','segments','components','vertices','endpoints'},
    'Q07': {'accounts'},
    'Q08': set(),
    'Q09': {'queries','blockers','components'},
    'Q10': {'precincts','discrepancies'},
    'Q11': {'lots','bids','reasons','allocations'},
    'Q12': {'queries','claim_dependencies','publications','cited_versions','stale_versions','retracted_publications'},
    'Q13': {'queries','affected_assemblies','impacted_shipments','open_shipments','suppliers','retailers'},
    'Q14': {'jobs','cycles','members','waits_on'},
    'Q15': {'events','comparisons','causal_violations'},
    'Q16': set(),
    'Q17': {'nodes','members'},
    'Q18': {'crowns'},
    'Q19': {'nights','targets','light_curve','used_references','rejected_references'},
    'Q20': {'field','tracks'},
}

def normalize(task, value, field=''):
    if isinstance(value, dict):
        if set(value) == {'num', 'den'} and type(value['num']) is int and type(value['den']) is int and value['den']:
            fraction = Fraction(value['num'], value['den'])
            return {'num':fraction.numerator, 'den':fraction.denominator}
        return {k: normalize(task, v, k) for k, v in value.items()}
    if isinstance(value, list):
        if task == 'Q19' and field in {'zero_point','calibrated','residual','baseline'} and len(value)==2 and all(type(x) is int for x in value) and value[1]:
            fraction = Fraction(*value)
            return [fraction.numerator, fraction.denominator]
        items = [normalize(task, v) for v in value]
        if field in UNORDERED[task]:
            return sorted(items, key=lambda v: json.dumps(v, sort_keys=True))
        return items
    return value

def check_value(ident, name, actual, wanted, context=None):
    try:
        return json.dumps(normalize(ident, actual), sort_keys=True) == json.dumps(normalize(ident, wanted), sort_keys=True)
    except (TypeError, ValueError, OverflowError):
        return False
