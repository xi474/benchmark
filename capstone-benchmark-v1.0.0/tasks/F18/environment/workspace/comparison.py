from fractions import Fraction
import json

def fractions(x):
    if x is None:return None
    if not isinstance(x,list) or len(x)!=2 or any(type(v) is not int for v in x) or x[1]<=0:raise ValueError
    return Fraction(*x)

def normalize(ident,value,field=""):
    if ident in {"F18","F20"} and isinstance(value,list):
        q=fractions(value)
        return [q.numerator,q.denominator]
    if isinstance(value,dict):return {k:normalize(ident,v,k) for k,v in value.items()}
    return value

def check_value(ident,name,actual,wanted,context=None):
    try:
        if ident!="F17":
            return json.dumps(normalize(ident,actual),sort_keys=True)==json.dumps(normalize(ident,wanted),sort_keys=True)
        d=context.get("request",context);base=bytes.fromhex(d["base"]);out=bytearray();cost=head=0
        if set(actual)!={"cost","ops"} or type(actual["cost"]) is not int or not isinstance(actual["ops"],list):return False
        for op in actual["ops"]:
            if set(op)=={"literal"}:
                literal=bytes.fromhex(op["literal"])
                if not literal:return False
                out.extend(literal);cost+=d["literal_header"]+len(literal)*d["literal_unit"]
            elif set(op)=={"copy"}:
                offset,size=op["copy"]
                if type(offset) is not int or type(size) is not int or offset<0 or size<d["min_copy"] or offset+size>len(base):return False
                out.extend(base[offset:offset+size]);cost+=d["copy_header"]+abs(offset-head)*d["seek_unit"];head=offset+size
            else:return False
        return cost==actual["cost"]==wanted["cost"] and out==bytes.fromhex(d["target"])
    except (KeyError,TypeError,ValueError,ArithmeticError):
        return False
