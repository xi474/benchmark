"""Acceptance for non-unique outputs. No reference implementation imports."""
import sqlite3
import re
import base64
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import tarfile
import tempfile

HERE=Path(__file__).resolve().parent
_CACHE={}

def members(bundle):
    out=[]
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(bundle)),mode='r:*') as archive:
        for item in archive.getmembers():
            name=item.name.rstrip('/')
            if item.issym():out.append(dict(name=name,type='symlink',linkname=item.linkname))
            elif item.isdir():out.append(dict(name=name,type='dir'))
            elif item.isfile():out.append(dict(name=name,type='file',content=archive.extractfile(item).read().decode()))
            else:return None
    return sorted(out,key=lambda x:x['name'])

def archive_ok(actual,wanted):
    try:return actual['rejected']==wanted['rejected'] and members(actual['tar'])==members(wanted['tar'])
    except Exception:return False

def git_clean_ok(actual,wanted):
    try:
        with tempfile.TemporaryDirectory(prefix='git-verify-') as td:
            root=Path(td)
            with tarfile.open(fileobj=io.BytesIO(base64.b64decode(actual['bundle'])),mode='r:*') as archive:archive.extractall(root,filter='data')
            files={f.relative_to(root).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in root.rglob('*') if f.is_file() and '.git' not in f.relative_to(root).parts}
            cmd=['git','-C',str(root)]
            messages=subprocess.check_output(cmd+['log','--format=%s'],text=True,stderr=subprocess.DEVNULL).splitlines()
            names=subprocess.check_output(cmd+['cat-file','--batch-all-objects','--batch-check=%(objectname)'],text=True,stderr=subprocess.DEVNULL).splitlines()
            if any(b'secret[' in subprocess.check_output(cmd+['cat-file','-p',oid],stderr=subprocess.DEVNULL) for oid in names):return False
            return files==actual['files']==wanted['files'] and messages==actual['messages']==wanted['messages']
    except Exception:return False

def sql_database(tables):
    con=sqlite3.connect(':memory:');con.executescript('CREATE TABLE words(wordid INTEGER,word TEXT);CREATE TABLE senses(wordid INTEGER,synsetid INTEGER);CREATE TABLE synsets(synsetid INTEGER,domainid INTEGER,posid INTEGER);')
    for name,keys in [('words',['wordid','word']),('senses',['wordid','synsetid']),('synsets',['synsetid','domainid','posid'])]:con.executemany('INSERT INTO '+name+' VALUES ('+','.join('?' for k in keys)+')',[[r[k] for k in keys] for r in tables[name]])
    con.commit();con.execute('PRAGMA query_only=ON');return con

def sql_query_ok(sql):
    if not isinstance(sql,str):return False
    key=('sql',sql)
    if key in _CACHE:return _CACHE[key]
    cases=json.loads((HERE/'vectors/N21.json').read_text(encoding='utf-8'))['integration']
    try:
        for case in cases:
            tables=case['input']['tables'];budget=200*len(tables['senses'])+20000;steps=[0];con=sql_database(tables)
            def tick():steps[0]+=1;return int(steps[0]>budget)
            con.set_progress_handler(tick,1)
            try:
                cur=con.execute(sql);actual=dict(columns=[x[0] for x in cur.description],rows=[list(r) for r in cur.fetchall()])
                if actual!=case['results']['query_result']:raise ValueError('query result')
            finally:con.close()
        _CACHE[key]=True
    except Exception:_CACHE[key]=False
    return _CACHE[key]

def hook_ok(script,payload):
    if not isinstance(script,str):return False
    key=('hook',script)
    if key in _CACHE:return _CACHE[key]
    from fixture_runtime import run_deploy
    try:
        cases=json.loads((HERE/'vectors/N25.json').read_text(encoding='utf-8'))['integration']
        for case in cases:
            p=case['input']
            if run_deploy(script,p['routes'],p['batches'])!=case['results']['deployment_report']:raise ValueError('deployment')
        _CACHE[key]=True
    except Exception:_CACHE[key]=False
    return _CACHE[key]

def distribution_ok(name,value,payload):
    model=payload.get('model',payload);n=model.get('n');targets=model.get('targets',{'forward':10.,'backward':10.})
    try:
        if name=='distribution':
            if not isinstance(value,list) or len(value)!=n or any(not math.isfinite(x) or x<=0 for x in value):return False
            mass=math.fsum(value);forward=math.fsum(x*math.log(x*n) for x in value);backward=math.fsum(math.log(1/(x*n)) for x in value)/n
            return abs(mass-1)<=1e-5 and abs(forward-targets['forward'])<=.001 and abs(backward-targets['backward'])<=.001
        return value['size']==n and abs(value['mass']-1)<=1e-5 and abs(value['forward_kl']-targets['forward'])<=.001 and abs(value['backward_kl']-targets['backward'])<=.001 and value['meets_target'] is True
    except Exception:return False

def ics_record(text):
    lines=text.replace('\r\n','\n').splitlines()
    assert lines[0]=='BEGIN:VCALENDAR' and lines[-1]=='END:VCALENDAR'
    assert 'BEGIN:VEVENT' in lines and 'END:VEVENT' in lines
    fields={line.split(':',1)[0]:line.split(':',1)[1] for line in lines if ':' in line}
    return dict(start=fields['DTSTART'],end=fields['DTEND'],summary=fields['SUMMARY'],attendees=[line.split(':mailto:',1)[1] for line in lines if line.startswith('ATTENDEE:mailto:')])

def bool_values(ast,rows):
    def ev(a,r):
        if isinstance(a,str):return bool(r[a])
        x=[ev(y,r) for y in a['args']]
        if a['op']=='and':return all(x)
        if a['op']=='or':return any(x)
        return sum(x)%2==1
    return [ev(ast,r) for r in rows]

def sql_bool_ok(value,payload):
    try:
        con=sqlite3.connect(':memory:')
        try:actual=[bool(con.execute('SELECT ('+value['sql']+')',r).fetchone()[0]) for r in payload['rows']]
        finally:con.close()
        return value['values']==actual==bool_values(payload['ast'],payload['rows'])
    except Exception:return False
