import json

UNORDERED={"F01":{"pages"},"F02":{"frontier"},"F03":{"differences"},"F04":set(),"F05":{"inputs"},"F06":{"margins"}}

def normalize(ident,value,field=""):
    if isinstance(value,dict):
        return {k:normalize(ident,v,k) for k,v in value.items()}
    if isinstance(value,list):
        rows=[normalize(ident,v) for v in value]
        if field in UNORDERED[ident]:
            rows.sort(key=lambda r:json.dumps(r,sort_keys=True))
        return rows
    if ident=="F01" and field in {"old_image","new_image","bytes_hex"} and isinstance(value,str):
        return bytes.fromhex(value).hex()
    return value

def check_value(ident,name,actual,wanted,context=None):
    try:
        return json.dumps(normalize(ident,actual),sort_keys=True)==json.dumps(normalize(ident,wanted),sort_keys=True)
    except (TypeError,ValueError):
        return False
