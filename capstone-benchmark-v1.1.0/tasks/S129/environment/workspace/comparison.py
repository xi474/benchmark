def normalize(ident,v):
    return {**v,'forward_batches':[sorted(b) for b in v['forward_batches']],
        'compensation_batches':[sorted(b) for b in v['compensation_batches']],
        'failed_actions':sorted(v['failed_actions']),'unresolved':sorted(v['unresolved'])}


def check_value(task,component,actual,expected,request=None):
    # The one public worked instance has a unique optimal batch partition.
    # Full arbitrary-optimum trace replay lives only in the separate hidden evaluator.
    try:return normalize(task,actual)==normalize(task,expected)
    except (TypeError,ValueError,KeyError,AttributeError):return False
