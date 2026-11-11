"""Author algorithms for additional tasks. Never imported by the verifier."""
import copy
from datetime import datetime,timedelta,timezone
from fractions import Fraction
import json
import re
import sqlite3

def eval_bool(ast,row):
    if isinstance(ast,str):return bool(row[ast])
    values=[eval_bool(a,row) for a in ast['args']]
    return all(values) if ast['op']=='and' else any(values) if ast['op']=='or' else sum(values)%2==1

def bool_sql(ast):
    if isinstance(ast,str):return ':'+ast
    terms=[bool_sql(a) for a in ast['args']]
    return '('+(' AND ' if ast['op']=='and' else ' OR ').join(terms)+')' if ast['op']!='xor' else '(('+ '+'.join('CASE WHEN '+x+' THEN 1 ELSE 0 END' for x in terms)+') % 2 = 1)'

def parse_expr(text):
    tokens=re.findall(r'\\frac|[0-9]+|[a-zA-Z]|[{}()+*^]',text);index=0
    def atom():
        nonlocal index
        t=tokens[index];index+=1
        if t=='\\frac':
            assert tokens[index]=='{';index+=1;a=expr();assert tokens[index]=='}';index+=1
            assert tokens[index]=='{';index+=1;b=expr();assert tokens[index]=='}';index+=1
            value=['div',a,b]
        elif t in '{(':
            value=expr();assert tokens[index]==('}' if t=='{' else ')');index+=1
        else:value=['int',int(t)] if t.isdigit() else ['var',t]
        if index<len(tokens) and tokens[index]=='^':index+=1;value=['pow',value,atom()]
        return value
    def product():
        nonlocal index
        value=atom()
        while index<len(tokens) and tokens[index]=='*':index+=1;value=['mul',value,atom()]
        return value
    def expr():
        nonlocal index
        value=product()
        while index<len(tokens) and tokens[index]=='+':index+=1;value=['add',value,product()]
        return value
    value=expr();assert index==len(tokens);return value

def expr_value(ast,values):
    op=ast[0]
    if op=='int':return Fraction(ast[1])
    if op=='var':return Fraction(values[ast[1]])
    a,b=expr_value(ast[1],values),expr_value(ast[2],values)
    return a+b if op=='add' else a*b if op=='mul' else a/b if op=='div' else a**int(b)

def render_expr(ast):
    if ast[0] in ['int','var']:return str(ast[1])
    return '('+render_expr(ast[1])+{'add':'+','mul':'*','div':'/','pow':'^'}[ast[0]]+render_expr(ast[2])+')'

def extra_solve(op,p,c):
    if op=='variable_plan':
        out=copy.deepcopy(p['dataset']['variables'])
        for value in out.values():value['dims']=[p['swap'].get(x,x) for x in value['dims']]
        return out
    if op=='coordinate_plan':
        return dict(coords=sorted(set(p['dataset']['coords'])|set(p['swap'].values())),indexes={name:copy.deepcopy(p['dataset']['variables'][name]['data']) for name in p['swap'].values()})
    if op=='apply_swap':return dict(variables=copy.deepcopy(p['variables']),**copy.deepcopy(p['coordinates']))
    if op=='c3':
        def lin(name):
            bases=p['classes'][name]['bases'];seqs=[lin(b) for b in bases]+[list(bases)];out=[name]
            while any(seqs):
                seqs=[s for s in seqs if s]
                head=next(s[0] for s in seqs if not any(s[0] in other[1:] for other in seqs));out.append(head)
                for s in seqs:
                    if s and s[0]==head:s.pop(0)
            return out
        return lin(p['target'])
    if op=='local_marks':return {name:copy.deepcopy(x['marks']) for name,x in p['classes'].items()}
    if op=='merge_marks':return dict(mro=p['mro'],marks=[copy.deepcopy(x) for name in p['mro'] for x in p['local'][name]])
    if op=='native_bool':return [eval_bool(p['ast'],row) for row in p['rows']]
    if op=='fallback_bool':
        sql=bool_sql(p['ast']);con=sqlite3.connect(':memory:')
        try:return dict(sql=sql,values=[bool(con.execute('SELECT '+sql,row).fetchone()[0]) for row in p['rows']])
        finally:con.close()
    if op=='xor_report':
        assert p['native']==p['fallback']['values']
        return dict(values=p['native'],selected_ids=[row['id'] for row,flag in zip(p['rows'],p['native']) if flag])
    if op in ['timezone_a','timezone_b']:
        out=[]
        for row in p['rows']:
            dt=datetime.fromisoformat(row['local'])
            if op=='timezone_a':dt=dt+timedelta(minutes=p['target']-p['source'])
            else:dt=dt.replace(tzinfo=timezone(timedelta(minutes=p['source']))).astimezone(timezone(timedelta(minutes=p['target'])))
            out.append(dict(id=row['id'],date=dt.date().isoformat()))
        return out
    if op=='date_report':
        assert p['a']==p['b'];return dict(dates=p['a'],selected_ids=[r['id'] for r in p['a'] if r['date']==p['date']])
    if op=='query_symbols':return {side:sorted(p[side]['tables']) for side in ['left','right']}
    if op=='alias_map':
        used=set(p['symbols']['left']+p['symbols']['right']);out={};index=0
        for old in p['symbols']['right']:
            while 'T'+str(index) in used:index+=1
            out[old]='T'+str(index);used.add(out[old]);index+=1
        return out
    if op=='rewrite_aliases':
        m=p['mapping'];right=[{**row,'alias':m[row['alias']]} for row in p['right']['clauses']]
        return dict(tables={**p['left']['tables'],**{m[k]:v for k,v in p['right']['tables'].items()}},branches=[p['left']['clauses'],right])
    if op=='parse_fraction':return parse_expr(p['latex'])
    if op=='eval_fraction':
        value=expr_value(p['ast'],p['values']);return dict(numerator=value.numerator,denominator=value.denominator)
    if op=='fraction_report':return dict(ast=p['ast'],value=p['value'],text=render_expr(p['ast']))
    if op=='log_snapshot':return copy.deepcopy(p['initial'])
    if op=='log_capture':
        state=copy.deepcopy(p['initial']);captured=[]
        for event in p['events']:
            if event['kind']=='set':state['handler']=state['loggers'][event['logger']]=event['level']
            elif event['level']>=max(state['handler'],state['loggers'][event['logger']]):captured.append(event['text'])
        return dict(state=state,captured=captured)
    if op=='log_restore':
        state=copy.deepcopy(p['snapshot']);out=[e['text'] for e in p['next_events'] if e['level']>=max(state['handler'],state['loggers'][e['logger']])]
        return dict(restored=state,captured=p['capture']['captured'],next_captured=out)
    from references_more import more_solve
    return more_solve(op,p,c)
