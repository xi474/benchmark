"""Author-only helpers; never installed in a candidate workspace."""
from __future__ import annotations
import copy, hashlib, json, math, re
from pathlib import PurePosixPath

OPS={}
RULES={}
def operation(name,rule):
    def wrap(fn):
        OPS[name]=fn; RULES[name]=rule.strip(); return fn
    return wrap

def require(test,message='invalid input'):
    if not test: raise ValueError(message)
def obj(v): require(type(v) is dict,'object required'); return v
def seq(v): require(type(v) is list,'array required'); return v
def text(v,empty=False):
    require(type(v) is str and (empty or bool(v.strip())),'text required'); return v
def integer(v,minimum=None):
    require(type(v) is int and (minimum is None or v>=minimum),'integer required'); return v
def number(v):
    require(type(v) in (int,float) and math.isfinite(v),'finite number required'); return v
def boolean(v): require(type(v) is bool,'boolean required'); return v
def field(v,k):
    obj(v); require(k in v,'missing '+k); return v[k]
def rows(v,k): return seq(field(v,k))
def string(v,k,empty=False): return text(field(v,k),empty)
def ints(v,k,minimum=None): return integer(field(v,k),minimum)
def unique(rows_,key='id'):
    seen=set()
    for r in rows_:
        x=string(r,key); require(x not in seen,'duplicate '+key); seen.add(x)
    return rows_
def safe_path(p):
    text(p); q=PurePosixPath(p)
    require(not q.is_absolute() and '\\' not in p and ':' not in p and all(x not in ('','.','..') for x in p.split('/')),'unsafe relative path')
    return p
def valid_json(v):
    if type(v) is float: require(math.isfinite(v),'nonfinite JSON')
    elif type(v) is dict:
        for k,x in v.items(): text(k,True); valid_json(x)
    elif type(v) is list:
        for x in v: valid_json(x)
    else: require(v is None or type(v) in (str,int,bool),'not JSON')
def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def raw(payloads,i=0):
    p=payloads[i]
    if type(p) is dict and set(p)=={'name','result'}: return obj(p['result'])
    return obj(p)
def evaluate(payloads,contract):
    valid_json(payloads); valid_json(contract)
    seq(payloads); obj(contract); require(len(payloads)==len(rows(contract,'inputs')),'payload count')
    try:
        result=OPS[contract['operation']](copy.deepcopy(payloads),copy.deepcopy(contract))
    except (KeyError,TypeError,IndexError,AttributeError,OverflowError) as exc:
        raise ValueError('invalid business input: '+str(exc)) from exc
    obj(result); valid_json(result)
    return {'name':contract['name'],'result':result}

def component(name,op,deps=None,**params):
    return {'name':name,'operation':op,'inputs':['inputs/case.json'] if deps is None else deps,'output':f'outputs/{name}.json',**params}
def output(name): return f'outputs/{name}.json'

TASKS=[]
def task(id,slug,style,components,fixture):
    TASKS.append(dict(id=id,slug=slug,style=style,components=components,fixture=fixture))
