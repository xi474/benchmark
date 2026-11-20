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
    t,a=get('MP04'); v=value(a,'directory'); assert len(v['users'])==15 and next(x for x in v['users'] if x['id']=='110')['email']=='10@b'; assert any(x['field']=='name' for x in v['conflicts']); results.append('MP04: union IDs and missing/empty precedence')
    t,a=get('MP08'); assert value(a,'classify')['missing']==['winter'] and len(value(a,'outbox')['attachments'])==8; assert all(x.startswith('holiday/') for x in value(a,'outbox')['attachments']); results.append('MP08: partial success and post-move paths')
    t,a=get('MP09'); d=t['fixture'](1); candidates=[minute for minute in range(d['now'],1201) if all(any(w['start']<=q<w['end'] for w in d['windows']) and not any(b['start']<=q<b['end'] for b in d['busy']) for q in range(minute,minute+d['duration']))]; first=min(candidates); second=min(x for x in candidates if x>=first+d['duration']+d['gap']); assert value(a,'calendar')['slots']==[dict(start=x,end=x+d['duration']) for x in [first,second]]; results.append('MP09: independent minute-grid interval enumeration')
    t,a=get('MP10',2); assert value(a,'dinner')['start']=='2026-11-11T19:00'; assert value(a,'shopping')['recipient']=='c2-7' and value(a,'shopping')['total_cents']==1098; results.append('MP10: calendar and integer-price calculation')
    t,a=get('MP11'); assert value(a,'ride')['pickup']==470; assert value(a,'cancellations')['cancelled']==['e1','e3','e7','e9']; results.append('MP11: cancellation/seminar distinction')
    t,a=get('MP24'); assert value(a,'query')['professors']==[dict(id='p1',countries=['DE','US'],eligible_departments=['b'])]; results.append('MP24: 6+6 counterexample and independent EU/count departments')
    return results
