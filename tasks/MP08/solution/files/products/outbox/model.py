import json, math
from pathlib import Path

def load_payload(path):
    def finite(v):
        if isinstance(v,float) and not math.isfinite(v): raise ValueError('nonfinite JSON')
        if isinstance(v,dict):
            for x in v.values(): finite(x)
        if isinstance(v,list):
            for x in v: finite(x)
    try: data=json.loads(Path(path).read_text(encoding='utf-8'))
    except (ValueError,UnicodeError) as e: raise ValueError('invalid JSON') from e
    if type(data) not in (dict,list): raise ValueError('JSON object/array required')
    finite(data)
    return data
