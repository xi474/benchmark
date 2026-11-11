"""Generate local synthetic binary fixtures once; never copy oracle metadata to agents."""
import base64
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parent

def encoded(data):return base64.b64encode(data).decode()
def archive(folder):
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w:gz') as tar:
        for p in sorted(folder.rglob('*')):
            if p.is_file():tar.add(p,arcname=p.relative_to(folder).as_posix())
    return encoded(buffer.getvalue())

def git(args,root):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL,text=True)

def fixtures():
    path=ROOT/'fixtures/binary.json'
    if path.exists():return json.loads(path.read_text(encoding='utf-8'))
    parent=ROOT.parent/'.tmp';parent.mkdir(exist_ok=True);out={'git':[],'wal':[]}
    for seed in [1,2,3]:
        with tempfile.TemporaryDirectory(dir=parent,prefix='binary-fixture-') as td:
            root=Path(td);repo=root/'repo';repo.mkdir();git(['init','-q'],repo);git(['config','user.name','Fixture'],repo);git(['config','user.email','fixture@example.invalid'],repo);git(['config','gc.auto','0'],repo)
            (repo/'README.txt').write_text('normal-'+str(seed),encoding='utf-8');git(['add','.'],repo);git(['commit','-qm','init'],repo)
            secret=f'secret[synthetic_medium30_{seed}_object]';(repo/'lost.txt').write_text(secret,encoding='utf-8');git(['add','.'],repo);git(['commit','-qm','temporary data'],repo);git(['reset','--hard','HEAD~1'],repo)
            (repo/'notes.txt').write_text('keep-'+str(seed),encoding='utf-8');git(['add','.'],repo);git(['commit','-qm','keep notes'],repo)
            files={p.relative_to(repo).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in repo.iterdir() if p.is_file()}
            out['git'].append(dict(request={'bundle':archive(repo)},expected=dict(secret=secret,files=files,messages=['keep notes','init'],remaining_secret_objects=0)))
            db=root/'source.db';con=sqlite3.connect(db);con.execute('PRAGMA journal_mode=WAL');con.execute('CREATE TABLE items(id INTEGER PRIMARY KEY,name TEXT,value INTEGER)')
            n=5 if seed==1 else seed+2;initial=[(i,'item'+str(i),seed*100+i) for i in range(1,n+1)];con.executemany('INSERT INTO items VALUES (?,?,?)',initial);con.commit();con.execute('PRAGMA wal_checkpoint(TRUNCATE)');base=db.read_bytes()
            con.execute('UPDATE items SET value=value+50 WHERE id<=2');extra=6 if seed==1 else seed+1;con.executemany('INSERT INTO items VALUES (?,?,?)',[(n+i,'new'+str(i),seed*200+i) for i in range(1,extra+1)]);con.commit();wal=Path(str(db)+'-wal').read_bytes();rows=[dict(id=i,name=n,value=v) for i,n,v in con.execute('SELECT id,name,value FROM items ORDER BY id')];con.close();key=31+seed
            out['wal'].append(dict(request={'base_b64':encoded(base),'encoded_wal_b64':encoded(bytes(b^key for b in wal)),'codec':{'scheme':'xor-byte','key':key}},expected=rows,original_wal_b64=encoded(wal)))
    path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');return out

def query_data(count):
    words=[dict(wordid=i,word='word_'+str(i)) for i in range(1,count+1)]
    synsets=[dict(synsetid=j,domainid=j%3,posid=j%2) for j in range(1,5)]
    senses=[]
    for word in words:
        for j in range(1,4):
            senses.extend(dict(wordid=word['wordid'],synsetid=j) for _ in range(1+(word['wordid']+j)%4))
    return dict(words=words,synsets=synsets,senses=senses)
