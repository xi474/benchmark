"""Small-instance oracles using different representations from the author solver."""
import copy
from datetime import datetime,timedelta
from fractions import Fraction
import re

def extra_expected(kind,p):
    if kind=='swap_immutable':
        v={}
        for name,item in p['dataset']['variables'].items():v[name]={'dims':[p['swap'][d] if d in p['swap'] else d for d in item['dims']],'data':item['data'][:],'attrs':dict(item['attrs'])}
        return dict(variables=v,coords=sorted(set(p['dataset']['coords']+list(p['swap'].values()))),indexes={n:list(p['dataset']['variables'][n]['data']) for n in p['swap'].values()})
    if kind=='python_mro':
        classes={}
        def cls(name):
            if name not in classes:classes[name]=type(name,tuple(cls(b) for b in p['classes'][name]['bases']),{'own':p['classes'][name]['marks']})
            return classes[name]
        names=[c.__name__ for c in cls(p['target']).__mro__ if c is not object]
        return dict(mro=names,marks=[item for n in names for item in p['classes'][n]['marks']])
    if kind=='boolean_truth':
        def evaluate(x,row):
            if isinstance(x,str):return bool(row[x])
            children=[evaluate(a,row) for a in x['args']]
            if x['op']=='and':return False not in children
            if x['op']=='or':return True in children
            flag=False
            for value in children:flag=flag!=value
            return flag
        values=[evaluate(p['ast'],r) for r in p['rows']];return dict(values=values,selected_ids=[r['id'] for r,v in zip(p['rows'],values) if v])
    if kind=='timezone_projection':
        epoch=datetime(1970,1,1);out=[]
        for r in p['rows']:
            seconds=(datetime.fromisoformat(r['local'])-epoch).total_seconds()-p['source']*60+p['target']*60
            out.append(dict(id=r['id'],date=(epoch+timedelta(seconds=seconds)).date().isoformat()))
        return dict(dates=out,selected_ids=[r['id'] for r in out if r['date']==p['date']])
    if kind=='alias_identity':
        names=sorted(p['right']['tables']);unavailable=set(p['left']['tables'])|set(names);available=[f'T{i}' for i in range(100) if f'T{i}' not in unavailable];pairs=list(zip(names,available));mapping=dict(pairs)
        result=copy.deepcopy(p['left']['tables']);result.update((mapping[a],table) for a,table in p['right']['tables'].items())
        return dict(tables=result,branches=[p['left']['clauses'],[{'alias':mapping[x['alias']],'field':x['field'],'value':x['value']} for x in p['right']['clauses']]])
    if kind=='fraction_numeric':
        # Golden ASTs are hand-specified; the oracle does not parse with the solver.
        known={r'\frac{\frac{a}{c}}{\frac{1}{c^2}}':['div',['div',['var','a'],['var','c']],['div',['int',1],['pow',['var','c'],['int',2]]]],r'\frac{1+2}{\frac{3}{4}}':['div',['add',['int',1],['int',2]],['div',['int',3],['int',4]]],r'\frac{x^2+1}{2}*3':['mul',['div',['add',['pow',['var','x'],['int',2]],['int',1]],['int',2]],['int',3]]}
        ast=known[p['latex']]
        def visit(node):
            if node[0]=='int':return Fraction(node[1]),str(node[1])
            if node[0]=='var':return Fraction(p['values'][node[1]]),node[1]
            a,aa=visit(node[1]);b,bb=visit(node[2]);symbol={'add':'+','mul':'*','div':'/','pow':'^'}[node[0]]
            value=a+b if symbol=='+' else a*b if symbol=='*' else a/b if symbol=='/' else a**int(b)
            return value,f'({aa}{symbol}{bb})'
        value,text=visit(ast);return dict(ast=ast,value=dict(numerator=value.numerator,denominator=value.denominator),text=text)
    if kind=='log_state_machine':
        handler=p['initial']['handler'];levels=dict(p['initial']['loggers']);texts=[]
        for e in p['events']:
            if e['kind']=='set':handler=e['level'];levels[e['logger']]=e['level']
            elif e['level']>=handler and e['level']>=levels[e['logger']]:texts.append(e['text'])
        nexttexts=[e['text'] for e in p['next_events'] if e['level']>=p['initial']['handler'] and e['level']>=p['initial']['loggers'][e['logger']]]
        return dict(restored=copy.deepcopy(p['initial']),captured=texts,next_captured=nexttexts)
    from oracles_more import more_expected
    return more_expected(kind,p)
