"""Hand-calculated cases and independent library/property checks of author references."""
from __future__ import annotations
import copy, decimal, io, sqlite3, zipfile
from email import policy
from email.parser import BytesParser
from reference import TASKS,evaluate,canonical
from vectors import available

def run():
    results=[]
    def get(id_,seed=1,case=None):
        t=next(t for t in TASKS if t['id']==id_); return t,available(t,t['fixture'](seed) if case is None else case)
    def value(a,name):return a['outputs/'+name+'.json']['result']
    t,a=get('MP01'); assert value(a,'hard')['predictions']==['blue','red','red','blue']; assert value(a,'soft')['predictions']==['blue','red','blue','red']; assert len(value(a,'fit')['members'])==3; results.append('MP01: hand weighted/class-column case')
    t,a=get('MP02'); v=value(a,'table'); assert v['columns']==['a','c','b'] and v['coordinates']==list(range(8)); assert v['data'][0]==[10,1,0] and v['attribute_conflicts']==['site']; results.append('MP02: hand coordinate/data alignment')
    t,a=get('MP03'); v=value(a,'merged'); assert next(x for x in v['records'] if x['mount']=='/with space')['fstype']=='xfs'; assert len(next(x for x in v['conflicts'] if x['mount']=='/data')['evidence'])==3; results.append('MP03: escaped path and three-source conflict')
    t,a=get('MP04'); v=value(a,'directory'); assert len(v['users'])==15 and next(x for x in v['users'] if x['id']=='110')['email']=='10@b'; assert any(x['field']=='name' for x in v['conflicts']); results.append('MP04: union IDs and missing/empty precedence')
    t,a=get('MP05'); assert value(a,'ranking')['winner']=='c1-7' and len(value(a,'ranking')['ranking'])==8; results.append('MP05: independent duration/age arithmetic')
    t,a=get('MP06'); assert value(a,'calendar')['cancelled']==['e1-1','e1-4','e1-5']; assert value(a,'notifications')['unreachable']==['c2']; assert all(x['requires']==value(a,'calendar')['cancelled'] for x in value(a,'notifications')['outbox']); results.append('MP06: pre-cancel recipient snapshot and ordering')
    t,a=get('MP07'); assert value(a,'archive')['blocked'] and not value(a,'archive')['moves']; assert value(a,'archive')['deleted']==['home/tmp/a.tmp']; t,a=get('MP07',2); assert len(value(a,'archive')['moves'])==2; results.append('MP07: all-success gate and isolated cleanup')
    t,a=get('MP08'); assert value(a,'classify')['missing']==['winter'] and len(value(a,'outbox')['attachments'])==8; assert all(x.startswith('holiday/') for x in value(a,'outbox')['attachments']); results.append('MP08: partial success and post-move paths')
    t,a=get('MP09'); d=t['fixture'](1); candidates=[minute for minute in range(d['now'],1201) if all(any(w['start']<=q<w['end'] for w in d['windows']) and not any(b['start']<=q<b['end'] for b in d['busy']) for q in range(minute,minute+d['duration']))]; first=min(candidates); second=min(x for x in candidates if x>=first+d['duration']+d['gap']); assert value(a,'calendar')['slots']==[dict(start=x,end=x+d['duration']) for x in [first,second]]; results.append('MP09: independent minute-grid interval enumeration')
    t,a=get('MP10',2); assert value(a,'dinner')['start']=='2026-11-11T19:00'; assert value(a,'shopping')['recipient']=='c2-7' and value(a,'shopping')['total_cents']==1098; results.append('MP10: calendar and integer-price calculation')
    t,a=get('MP11'); assert value(a,'ride')['pickup']==470; assert value(a,'cancellations')['cancelled']==['e1','e3','e7','e9']; results.append('MP11: cancellation/seminar distinction')
    t,a=get('MP12'); assert value(a,'mail')['trash_ids']==['m1','m3','m5']; assert value(a,'reply')['email_id']=='m7'; assert any(x['path']=='Downloads/nested/c.pdf' for x in value(a,'commit')['files']); results.append('MP12: subtree and exact reply target')
    t,a=get('MP13'); v=value(a,'union'); assert len(v['index'])==4; row=v['data'][v['index'].index('g0')]; assert row[v['columns'].index('num.sum')]==14; assert row[v['columns'].index('time.span')] is None; results.append('MP13: aggregate index and missing branch')
    t,a=get('MP14',0); assert [x['id'] for x in value(a,'chain')['chain']]==['outer']; t,a=get('MP14',1); assert [x['id'] for x in value(a,'chain')['chain']]==['inner','outer']; assert value(a,'frames')['frames']['inner'][0]['file']=='module.py'; results.append('MP14: cause/context suppression and portable frames')
    t,a=get('MP15'); assert value(a,'analysis')['unused']==['module:os']; assert next(x for x in value(a,'analysis')['imports'] if x['name']=='abc')['used_by']==['comment']; _,a=get('MP15',case={'source':'import os\ndef f(os: os.PathLike):\n    return os\n'}); assert value(a,'analysis')['unused']==[]; results.append('MP15: independent annotation/type-comment and signature-scope regressions')
    t,a=get('MP16'); v=value(a,'document'); assert v['provider']=='Base' and next(x for x in v['parameters'] if x['name']=='y')['type']=='base.Item'; assert v['overloads'][0]['parameters'][1]['kind']=='kwonly'; results.append('MP16: parent namespace and overload kind')
    t,a=get('MP17'); v=value(a,'body'); message=BytesParser(policy=policy.default).parsebytes(('Content-Type: '+v['content_type']+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+bytes.fromhex(v['body_hex'])); parts={x.get_param('name',header='content-disposition'):x for x in message.iter_parts()}; assert parts['attachment'].get_payload(decode=True)==bytes(range(128)); assert parts['inline'].get_payload(decode=True)=='é text'.encode(); assert parts['inline']['Content-Transfer-Encoding'] is None; results.append('MP17: independent stdlib MIME parser')
    t,a=get('MP18'); assert value(a,'selection')['selected']==['README.md','plugins/a.py']; results.append('MP18: ordered directives and mandatory exclusions')
    t,a=get('MP19'); v=value(a,'payload'); z=zipfile.ZipFile(io.BytesIO(bytes.fromhex(v['zip_hex']))); assert 'unused.py' not in z.namelist() and z.read('main.py')==t['fixture'](1)['modules']['main.py'].encode(); assert all(x.date_time==(1980,1,1,0,0,0) for x in z.infolist()); results.append('MP19: independent ZIP reader and byte checks')
    t,a=get('MP20',3); assert value(a,'references')['error']['kind']=='segment'; assert value(a,'snapshot')['snapshot']==t['fixture'](3)['old_snapshot']; t,a=get('MP20',1); assert value(a,'snapshot')['committed']; results.append('MP20: schema/reference boundary and atomic rollback')
    t,a=get('MP21'); v=value(a,'query'); db=sqlite3.connect(':memory:'); db.execute('CREATE TABLE playlists(id TEXT,name TEXT,track_count INTEGER,duration REAL)'); db.executemany('INSERT INTO playlists VALUES(?,?,?,?)',[('a','Mix',4,9),('b',"O'Reilly",3,5),('c','Few',1,1)]); assert db.execute(v['sql'],v['params']).fetchall()==[('a',)]; assert '#EXTINF:4,A - Title 1-3\n' in value(a,'export')['m3u']; results.append('MP21: independent SQLite execution and half-up formatting')
    t,a=get('MP22'); r=value(a,'catalog')['records'][0]; assert r['languages']==['eng','ger','lat']; assert r['subjects']['organizations']==[dict(value='Jesuits. Dept.',count=2)]; assert r['authors'][0]['alternates']==['作者']; results.append('MP22: hand MARC count, link and language vectors')
    t,a=get('MP23'); restored=value(a,'restore')['files']; assert restored==sorted(t['fixture'](1)['files'],key=lambda x:x['path']); layout=value(a,'layout'); dirs={}
    for f in layout['tree']:
        assert len(bytes.fromhex(f['hex']))<=layout['max_file_bytes']; bits=f['path'].split('/')
        for i,bit in enumerate(bits):dirs.setdefault('/'.join(bits[:i]),set()).add(bit)
    assert all(len(v)<=layout['max_entries'] for v in dirs.values()); results.append('MP23: independent original-byte and filesystem-cap properties')
    t,a=get('MP24'); assert value(a,'query')['professors']==[dict(id='p1',countries=['DE','US'],eligible_departments=['b'])]; results.append('MP24: 6+6 counterexample and independent EU/count departments')
    t,a=get('MP25'); v=value(a,'archive'); assert v['totals']==dict(invoice='4818.00',receipt='4814.00'); assert v['rows'][0]['total']=='1200.50'; results.append('MP25: exact decimal hand totals, Total over Due')
    t,a=get('MP26'); plan=value(a,'plan'); assert len(plan['added'])==9 and plan['cancelled']==['conflict1']; d=t['fixture'](1); d['events']=value(a,'apply')['events']; again=available(t,d); assert value(again,'plan')['added']==[] and value(again,'plan')['cancelled']==[] and value(again,'apply')['outbox']==[]; results.append('MP26: independent boundary expectations and replay idempotence')
    t=next(t for t in TASKS if t['id']=='MP26');invalid=t['fixture'](1);invalid['events'][0]['end']='2026-11-06T20:00'
    try:available(t,invalid)
    except ValueError:pass
    else:raise AssertionError('long existing dinner must be outside bounded subset')
    return results

if __name__=='__main__':
    import json
    print(json.dumps(run(),ensure_ascii=False,indent=2))
