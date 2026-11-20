import base64
from collections import Counter,defaultdict
import hashlib
import io
import json
import os
from pathlib import Path
import posixpath
import re
import sqlite3
import subprocess
import tarfile
import tempfile

QUERY='''WITH pairs AS (SELECT wordid,synsetid,COUNT(*) AS cnt FROM senses GROUP BY wordid,synsetid),
stats AS (SELECT s.wordid,COUNT(DISTINCT s.synsetid) AS total_synsets,COUNT(*) AS total_senses,COUNT(DISTINCT y.domainid) AS distinct_domains,COUNT(DISTINCT y.posid) AS distinct_posids FROM senses s JOIN synsets y ON y.synsetid=s.synsetid GROUP BY s.wordid),
ranked AS (SELECT wordid,synsetid,cnt,ROW_NUMBER() OVER(PARTITION BY wordid ORDER BY cnt DESC,synsetid ASC) AS rn FROM pairs)
SELECT w.wordid AS word_id,w.word,st.total_synsets,st.total_senses,st.distinct_domains,st.distinct_posids,r.synsetid AS top_synsetid,r.cnt AS top_synset_sense_count FROM stats st JOIN words w ON w.wordid=st.wordid JOIN ranked r ON r.wordid=w.wordid AND r.rn=1 WHERE st.total_synsets>=2 AND st.distinct_domains>=2 AND st.total_senses>=2 ORDER BY st.total_senses DESC,st.total_synsets DESC,st.distinct_domains DESC,w.wordid ASC LIMIT 500'''

def db_for(tables):
    con=sqlite3.connect(':memory:');con.executescript('CREATE TABLE words(wordid INTEGER,word TEXT);CREATE TABLE senses(wordid INTEGER,synsetid INTEGER);CREATE TABLE synsets(synsetid INTEGER,domainid INTEGER,posid INTEGER);')
    for name,keys in [('words',['wordid','word']),('senses',['wordid','synsetid']),('synsets',['synsetid','domainid','posid'])]:con.executemany('INSERT INTO '+name+' VALUES ('+','.join('?' for k in keys)+')',[[row[k] for k in keys] for row in tables[name]])
    con.commit();con.execute('PRAGMA query_only=ON');return con

def unpack(bundle,root):
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(bundle)),mode='r:*') as tar:tar.extractall(root,filter='data')
def pack(root):
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w:gz') as tar:
        for p in sorted(root.rglob('*')):
            tar.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
    return base64.b64encode(buffer.getvalue()).decode()
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL,text=True)
def git_state(root):
    objects=git(root,'cat-file','--batch-all-objects','--batch-check=%(objectname)').splitlines();secrets=[]
    for oid in objects:
        data=subprocess.check_output(['git','-C',str(root),'cat-file','-p',oid],stderr=subprocess.DEVNULL)
        secrets.extend(x.decode() for x in re.findall(rb'secret\[[^\]]+\]',data))
    return dict(files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts},messages=git(root,'log','--format=%s').splitlines(),secrets=secrets)

def tar_members(text):
    members=[]
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(text))) as tar:
        for m in tar.getmembers():
            name=m.name.rstrip('/')
            if m.issym():members.append(dict(name=name,type='symlink',linkname=m.linkname))
            elif m.isdir():members.append(dict(name=name,type='dir'))
            elif m.isfile():members.append(dict(name=name,type='file',content=tar.extractfile(m).read().decode()))
    return sorted(members,key=lambda x:x['name'])

def storage_solve(op,p,c):
    if op=='archive_plan':
        result=[];rejected=[];nodes={posixpath.normpath('/collection/'+n['path']):n for n in p['nodes']}
        for node in p['nodes']:
            path=posixpath.normpath('/collection/'+node['path'])
            if not path.startswith('/collection/'):
                rejected.append(node['path']);continue
            name=path[len('/collection/'):]
            if node['kind']=='file':entry=dict(name=name,type='file',content=node['content'])
            elif node['kind']=='dir':entry=dict(name=name,type='dir')
            else:
                target=posixpath.normpath(posixpath.join(posixpath.dirname(path),node['target']))
                if target=='/collection' or target.startswith('/collection/'):entry=dict(name=name,type='symlink',linkname=posixpath.relpath(target,posixpath.dirname(path)))
                else:entry=dict(name=name,type='file',content=p['external_files'][target])
            result.append(entry)
        return dict(members=sorted(result,key=lambda x:x['name']),rejected=sorted(rejected))
    if op=='build_archive':
        buffer=io.BytesIO()
        with tarfile.open(fileobj=buffer,mode='w') as tar:
            for row in p['plan']['members']:
                info=tarfile.TarInfo(row['name']);info.mode=0o755 if row['type']=='dir' else 0o644
                if row['type']=='symlink':info.type=tarfile.SYMTYPE;info.linkname=row['linkname'];tar.addfile(info)
                elif row['type']=='dir':info.type=tarfile.DIRTYPE;tar.addfile(info)
                else:data=row['content'].encode();info.size=len(data);tar.addfile(info,io.BytesIO(data))
        return dict(tar=base64.b64encode(buffer.getvalue()).decode(),rejected=p['plan']['rejected'])
    if op=='inspect_archive':return dict(members=tar_members(p['archive']['tar']),rejected=p['archive']['rejected'])
    if op=='word_statistics':
        t=p['tables'];syn={x['synsetid']:x for x in t['synsets']};out=[]
        for word in sorted(t['words'],key=lambda x:x['wordid']):
            senses=[x for x in t['senses'] if x['wordid']==word['wordid']];ids={x['synsetid'] for x in senses}
            out.append(dict(word_id=word['wordid'],word=word['word'],total_synsets=len(ids),total_senses=len(senses),distinct_domains=len({syn[i]['domainid'] for i in ids}),distinct_posids=len({syn[i]['posid'] for i in ids})))
        return out
    if op=='top_synsets':
        counts=defaultdict(Counter)
        for row in p['tables']['senses']:counts[row['wordid']][row['synsetid']]+=1
        return [dict(word_id=i,top_synsetid=min(counts[i],key=lambda s:(-counts[i][s],s)),top_synset_sense_count=max(counts[i].values())) for i in sorted(counts)]
    if op=='optimized_query':return QUERY
    if op=='execute_query':
        con=db_for(p['tables'])
        try:
            cur=con.execute(p['sql']);return dict(columns=[x[0] for x in cur.description],rows=[list(x) for x in cur.fetchall()])
        finally:con.close()
    if op=='git_object_scan':
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);unpack(p['bundle'],root);state=git_state(root);return dict(secret=state['secrets'][0])
    if op=='git_clean':
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);unpack(p['bundle'],root);assert p['scan']['secret'] in git_state(root)['secrets'];git(root,'reflog','expire','--expire=now','--all');git(root,'gc','--prune=now');git(root,'prune','--expire=now');state=git_state(root);assert not state['secrets'];return dict(bundle=pack(root),files=state['files'],messages=state['messages'])
    if op=='git_recovery_report':
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);unpack(p['cleaned']['bundle'],root);state=git_state(root);return dict(secret=p['scan']['secret'],files=state['files'],messages=state['messages'],remaining_secret_objects=len(state['secrets']))
    if op=='sqlite_base':
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'main.db';path.write_bytes(base64.b64decode(p['base_b64']));con=sqlite3.connect(path)
            try:return [dict(id=i,name=n,value=v) for i,n,v in con.execute('SELECT id,name,value FROM items ORDER BY id')]
            finally:con.close()
    if op=='decode_wal':return base64.b64encode(bytes(b^p['codec']['key'] for b in base64.b64decode(p['encoded_wal_b64']))).decode()
    if op=='recover_sqlite':
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'main.db';path.write_bytes(base64.b64decode(p['base_b64']));Path(str(path)+'-wal').write_bytes(base64.b64decode(p['wal_b64']));con=sqlite3.connect(path)
            try:rows=[dict(id=i,name=n,value=v) for i,n,v in con.execute('SELECT id,name,value FROM items ORDER BY id')]
            finally:con.close()
        return dict(records=rows,base_count=len(p['base']),database=p['base_b64'],wal=p['wal_b64'])
    if op=='branch_routes':return dict(p['routes'])
    if op=='deployment_hook':
        return '''import io,json,os,pathlib,shutil,subprocess,sys,tarfile,tempfile
routes=json.loads('''+repr(json.dumps(p['routes']))+''')
root=pathlib.Path(os.environ['MEDIUM30_DEPLOY_ROOT']);repo=os.path.abspath(os.environ['GIT_DIR'])
for line in sys.stdin:
 old,new,ref=line.split()
 if ref not in routes or set(new)=={'0'}:continue
 target=root/routes[ref];target.parent.mkdir(parents=True,exist_ok=True)
 data=subprocess.check_output(['git','--git-dir',repo,'archive',new])
 stage=pathlib.Path(tempfile.mkdtemp(dir=target.parent))
 with tarfile.open(fileobj=io.BytesIO(data)) as tar:tar.extractall(stage,filter='data')
 if target.exists():shutil.rmtree(target)
 os.replace(stage,target)
'''
    if op=='deployment_report':
        from runtime import run_deploy
        return run_deploy(p['hook'],p['routes'],p['batches'])
    if op=='probability_model':return p
    if op=='solve_distribution':
        import numpy as np
        from scipy.optimize import least_squares
        from scipy.special import softmax
        model=p['model'];groups=np.asarray(model['groups'],dtype=float);n=model['n'];targets=model['targets']
        def residual(z):
            masses=softmax(np.r_[z,0.]);prob=masses/groups
            return [float(np.sum(masses*np.log(prob*n)))-targets['forward'],float(np.sum(groups/n*np.log(1/(n*prob))))-targets['backward']]
        fit=least_squares(residual,[12.,11.],xtol=1e-12,ftol=1e-12,gtol=1e-12,max_nfev=200);masses=softmax(np.r_[fit.x,0.]);return np.repeat(masses/groups,groups.astype(int)).tolist()
    if op=='distribution_report':
        import numpy as np
        values=np.asarray(p['probabilities']);n=len(values);mass=float(values.sum());forward=float(np.sum(values*np.log(values*n)));backward=float(np.mean(np.log(1/(values*n))));target=p['model']['targets']
        return dict(size=n,mass=mass,forward_kl=forward,backward_kl=backward,meets_target=bool(abs(forward-target['forward'])<=.001 and abs(backward-target['backward'])<=.001 and abs(mass-1)<=1e-5 and np.all(values>0)))
    raise ValueError(op)
