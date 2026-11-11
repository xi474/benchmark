import ast
import base64
import calendar
import copy
import hashlib
from pathlib import Path
import re
import sqlite3
import tempfile
import zipfile

def config_chain(node):
    if isinstance(node,ast.Name):return [node.id]
    if isinstance(node,ast.Attribute):
        base=config_chain(node.value);return base+[node.attr] if base else []
    if isinstance(node,ast.Subscript) and isinstance(node.slice,ast.Constant) and isinstance(node.slice.value,str):
        base=config_chain(node.value);return base+[node.slice.value] if base else []
    return []

def final_solve(op,p,c):
    if op in ['migrate_notes','migrate_shelves']:
        rows=copy.deepcopy(p['rows']);old,new=p['old'],p['new'];stats=dict(rows_changed=0,rows_deleted=0,failed_deletes=0)
        if old!=new:
            if new in rows:
                if op=='migrate_notes':stats['failed_deletes']=1
                else:del rows[old];stats['rows_deleted']=1
            else:rows[new]=rows.pop(old);stats['rows_changed']=1
        return dict(rows=rows,stats=stats)
    if op=='migration_report':return p
    if op=='template_deps':
        out={}
        for name,text in p['templates'].items():
            found=set()
            for expression in re.findall(r'\{\{(.*?)\}\}',text,re.S):
                tree=ast.parse(expression.strip(),mode='eval')
                for node in ast.walk(tree):
                    chain=config_chain(node)
                    if chain and chain[0]=='conf':
                        key='.'.join(chain[1:]);matches=[x for x in p['options'] if key==x or key.startswith(x+'.')]
                        if matches:found.add(max(matches,key=len))
            out[name]=sorted(found)
        return out
    if op=='dependency_index':
        out={}
        for name,deps in p['dependencies'].items():
            for dep in deps:out.setdefault(dep,[]).append(name)
        return {k:sorted(v) for k,v in out.items()}
    if op=='affected_templates':return dict(dependencies=p['dependencies'],affected=sorted({name for dep in p['changed'] for name in p['reverse'].get(dep,[])}))
    if op=='repository_definition':return copy.deepcopy(p['definition'])
    if op=='transaction_routes':
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/'db.sqlite';write=sqlite3.connect(db);read=sqlite3.connect(db)
            for repo in [p['album'],p['artist']]:
                table=repo['table'];write.execute(f'CREATE TABLE {table}(id INTEGER PRIMARY KEY,name TEXT)');write.executemany(f'INSERT INTO {table} VALUES (?,?)',[(x['id'],x['name']) for x in p['initial'][table]])
            write.commit();active=False;reads=[];routes=[]
            for e in p['events']:
                if e['kind']=='begin':write.execute('BEGIN');active=True;continue
                if e['kind']=='commit':write.commit();active=False;continue
                table=p[e['repo']]['table'];con=write if active or e['kind']=='put' else read;routes.append('transaction' if active else 'write' if e['kind']=='put' else 'read')
                if e['kind']=='put':
                    con.execute(f'INSERT OR REPLACE INTO {table} VALUES (?,?)',(e['id'],e['name']))
                    if not active:con.commit()
                else:
                    row=con.execute(f'SELECT name FROM {table} WHERE id=?',(e['id'],)).fetchone();reads.append(row[0] if row else None)
            final={repo['table']:[dict(id=i,name=n) for i,n in read.execute('SELECT id,name FROM '+repo['table']+' ORDER BY id')] for repo in [p['album'],p['artist']]};read.close();write.close()
            return dict(reads=reads,routes=routes,final=final)
    if op in ['directory_resources','zip_resources']:
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            if op=='directory_resources':
                root=base/'resources';root.mkdir()
                for name,data in p['files'].items():
                    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data)
                archive=None
            else:
                archive=zipfile.ZipFile(base/'assets.zip','w')
                for name,data in p['files'].items():archive.writestr(name,data)
                archive.close();archive=zipfile.ZipFile(base/'assets.zip');root=zipfile.Path(archive)
            found=set()
            for pattern in p['patterns']:
                folder=root/pattern['directory']
                if not folder.exists():continue
                for item in folder.iterdir():
                    if item.is_file() and item.name.endswith(pattern['extension']):found.add(pattern['directory']+'/'+item.name)
            if archive:archive.close()
            return sorted(found)
    if op=='resource_cache':
        assert p['directory']==p['zip'];return {name:p['files'][name] for name in p['directory']}
    if op=='resource_reads':return dict(paths=sorted(p['cache']),values=[p['cache'][name] for name in p['requests']])
    if op=='rental_initial':
        saved=set(p['saved'])
        for item in p['properties']:
            if item['city']==p['city']:
                if p['low']<=item['price']<=p['high']:saved.add(item['id'])
                else:saved.discard(item['id'])
        return sorted(saved)
    if op=='rental_new':return [dict(at=e['at'],id=e['property']['id']) for e in sorted(p['events'],key=lambda x:(x['at'],x['property']['id'])) if 0<=e['at']<p['window'] and e['property']['city']==p['city'] and p['low']<=e['property']['price']<=p['high']]
    if op=='rental_report':return dict(saved=p['saved'],notifications=[dict(to=p['friend'],property=e['id'],at=e['at']) for e in p['new']])
    if op=='reply_batch':return [dict(email=e['id'],to=e['from'],at=p['window'],purpose='gift_reply') for e in sorted(p['emails'],key=lambda x:(x['at'],x['id'])) if 0<=e['at']<p['window']]
    if op=='gift_variant':return next(v['id'] for v in p['variants'] if all(v[k]==value for k,value in p['selection'].items()))
    if op=='gift_checkout':
        year,month,_=map(int,p['date'].split('-'));day=calendar.monthrange(year,month)[1]
        return dict(replies=p['replies'],order=dict(at=p['window']+30,variant=p['variant'],quantity=len({r['to'] for r in p['replies']})),reminder=dict(date=f'{year:04d}-{month:02d}-{day:02d}',all_day=True,title='Reminder: Hand Out Gifts'))
    if op=='group_members':return dict(id='group:new',title='Happy Astrid Day!',members=sorted(x['id'] for x in p['contacts'] if x['name'] in p['names']))
    if op=='evening_events':return sorted(e['id'] for e in p['events'] if e['start_minute']>=1200)
    if op=='threshold_actions':
        seen=set();trigger=None
        for e in sorted(p['messages'],key=lambda x:(x['at'],x['id'])):
            if e['group']==p['group']['id'] and e['sender'] in p['group']['members'] and 0<=e['at']<p['window']:
                seen.add(e['sender'])
                if len(seen)>=p['threshold']:trigger=e['at'];break
        return dict(group=p['group'],trigger_at=trigger,ride=None if trigger is None else dict(at=trigger,pickup='21:30',vehicle='van',**{'from':'home'},to='Tegnergatan 8'),notice=None if trigger is None else dict(at=trigger,meet='20:00'),deleted=[] if trigger is None else p['evening'])
    if op=='move_document':
        files=copy.deepcopy(p['files']);data=files.pop(p['source']);files[p['destination']]=data
        return dict(files=files,attachment=dict(path=p['destination'],content=data,sha256=hashlib.sha256(base64.b64decode(data)).hexdigest()))
    if op=='document_recipients':
        target={p['email_sender']}|{x['id'] for x in p['people'] if x['country']=='RU' and x['pilot']};teachers=[x for x in p['people'] if x['teacher'] and x['id']!=p['self']]
        return dict(target_email=sorted(target),messages=sorted(x['id'] for x in teachers if x['messages']),fallback_email=sorted(x['id'] for x in teachers if not x['messages']))
    if op=='document_delivery':
        a=p['moved']['attachment'];r=p['recipients'];info=dict(path=a['path'],sha256=a['sha256'])
        return dict(files=p['moved']['files'],target_email=dict(to=r['target_email'],**info),messages=dict(members=r['messages'],**info) if r['messages'] else None,fallback_email=dict(to=r['fallback_email'],**info) if r['fallback_email'] else None,attachment_content=a['content'])
    from references_storage import storage_solve
    return storage_solve(op,p,c)
