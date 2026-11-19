import json


def normalize(ident,value,field=""):
    if isinstance(value,dict):return {k:normalize(ident,v,k) for k,v in value.items()}
    if isinstance(value,list) and field in ("required","best"):return sorted(value)
    return value


def check_value(ident,name,actual,wanted,context=None):
    try:
        return json.dumps(normalize(ident,actual),sort_keys=True)==json.dumps(normalize(ident,wanted),sort_keys=True)
    except (ValueError,TypeError):return False
