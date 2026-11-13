from collections import defaultdict


def rank(vectors, dimension):
    null_count=sum(all((z&v).bit_count()%2==0 for v in vectors) for z in range(1<<dimension))
    return dimension-(null_count.bit_length()-1)


def replay(q, transmissions):
    packets={p['id']:p for p in q['packets']};contacts={c['id']:c for c in q['contacts']}
    received={k:set() for k in packets};completion={k:None for k in packets};last={};by_tick=defaultdict(list);used=[]
    for r in transmissions:
        t=r['tick'];c=contacts[r['contact']]
        if not isinstance(t,int) or not c['start']<=t<c['end']:raise ValueError('inactive contact')
        if {'packet':r['packet'],'vector':r['vector']} not in c['symbols']:raise ValueError('symbol not offered')
        by_tick[t].append(r)
    for t,rows in sorted(by_tick.items()):
        active={r['contact'] for r in rows};capacity={k:0 for k in active}
        for field in ['station','craft','group']:
            if len({contacts[k][field] for k in active})!=len(active):raise ValueError('resource conflict')
        for k in active:
            c=contacts[k];old=last.get(c['station'])
            if old and old[0]!=c['band'] and t-old[1]<=q['switch_cooldown']:raise ValueError('cooldown')
        for r in rows:
            p=packets[r['packet']];c=contacts[r['contact']]
            if (p['craft'],p['band'])!=(c['craft'],c['band']) or not p['release']<=t<p['deadline'] or completion[p['id']] is not None:raise ValueError('ineligible packet')
            if any(completion[k] is None or completion[k]>t for k in p['requires']):raise ValueError('not decoded at tick start')
            capacity[c['id']]+=1
        if any(v>contacts[k]['rate'] for k,v in capacity.items()):raise ValueError('rate')
        for r in rows:received[r['packet']].add(r['vector'])
        for k,p in packets.items():
            if completion[k] is None and rank(received[k],p['dimension'])==p['dimension']:completion[k]=t+1
        for k in active:last[contacts[k]['station']]=(contacts[k]['band'],t);used.append(dict(tick=t,contact=k))
    ranks={k:rank(received[k],p['dimension']) for k,p in packets.items()}
    score=dict(priority=sum(p['priority'] for k,p in packets.items() if completion[k] is not None),count=sum(v is not None for v in completion.values()),rank=sum(ranks.values()))
    return dict(score=score,packets=[dict(id=k,rank=ranks[k],completion=completion[k]) for k in packets],contacts=used,transmissions=transmissions)


def normalize(ident,value):return value


def check_value(task,component,actual,expected,request=None):
    try:
        q=request.get('request',request)
        if set(actual)!=set(expected) or actual['score']!=expected['score']:return False
        rebuilt=replay(q,actual['transmissions'])
        return rebuilt['score']==actual['score'] and sorted(actual['packets'],key=lambda x:x['id'])==sorted(rebuilt['packets'],key=lambda x:x['id']) and {(r['tick'],r['contact']) for r in actual['contacts']}=={(r['tick'],r['contact']) for r in rebuilt['contacts']}
    except (TypeError,ValueError,KeyError,AttributeError,IndexError):return False
