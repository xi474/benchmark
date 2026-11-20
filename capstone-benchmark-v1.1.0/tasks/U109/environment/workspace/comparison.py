def normalize(ident,value):
    return {**value,'ineligible_bids':sorted(value['ineligible_bids'])}


def check_value(task,component,actual,expected,request=None):
    try:return normalize(task,actual)==normalize(task,expected)
    except (TypeError,ValueError,KeyError,AttributeError):return False
