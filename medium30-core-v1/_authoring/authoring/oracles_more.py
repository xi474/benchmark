import copy
from datetime import datetime,timedelta
import itertools
import re

def more_expected(kind,p):
    if kind=='meeting_minute_scan':
        def parse(s):return datetime.strptime(s,'%Y%m%dT%H%M%SZ')
        busy={name:[(parse(a),parse(b)) for a,b in re.findall(r'DTSTART:(\d+T\d+Z)\s+DTEND:(\d+T\d+Z)',ics)] for name,ics in p['calendars'].items()}
        def available(person,t):
            rule=p['rules'][person];minute=t.hour*60+t.minute;end=min(rule['end'],rule['weekday_end'].get(str(t.weekday()),rule['end']))
            if not rule['start']<=minute<end or any(a<=minute<b for a,b in rule['breaks']):return False
            for a,b in busy[person]:
                extra=rule['late_buffer'];finish=b+timedelta(minutes=extra['minutes']) if extra and b.hour*60+b.minute>=extra['threshold'] else b
                if a<=t<finish:return False
            return True
        for day in sorted(p['days']):
            base=datetime.fromisoformat(day)
            for minute in range(1440-59):
                start=base+timedelta(minutes=minute)
                if all(available(person,start+timedelta(minutes=k)) for person in p['calendars'] for k in range(60)):
                    return dict(start=start.strftime('%Y%m%dT%H%M%SZ'),end=(start+timedelta(hours=1)).strftime('%Y%m%dT%H%M%SZ'),attendees=p['attendees'],summary='Team Planning Meeting')
        raise ValueError('fixture not feasible')
    if kind=='group_table_exhaustive':
        def mul(a,b):return tuple(a[b[i]] for i in range(len(a)))
        def group(gens):
            allperms=list(itertools.permutations(range(len(gens[0]))));valid={tuple(range(len(gens[0]))),*map(tuple,gens)}
            while True:
                new={mul(a,b) for a in valid for b in valid}
                if new<=valid:return sorted(valid)
                valid|=new
        source=group(p['generators']);target=group(p['images']);fixed={tuple(range(len(p['generators'][0]))):tuple(range(len(p['images'][0])))}
        fixed.update(zip(map(tuple,p['generators']),map(tuple,p['images'])));free=[x for x in source if x not in fixed]
        for images in itertools.product(target,repeat=len(free)):
            f={**fixed,**dict(zip(free,images))}
            if all(f[mul(a,b)]==mul(f[a],f[b]) for a in source for b in source):return dict(valid=True,mapping=[dict(source=list(k),target=list(f[k])) for k in source])
        return dict(valid=False,mapping=[])
    if kind=='dense_block_cube':
        blocks=p['matrix'];rs=[row[0]['rows'] for row in blocks];cs=[b['cols'] for b in blocks[0]];n=sum(rs);dense=[[0]*n for _ in range(n)];offset_r=0
        for i,row in enumerate(blocks):
            offset_c=0
            for j,b in enumerate(row):
                for r in range(b['rows']):
                    for c in range(b['cols']):dense[offset_r+r][offset_c+c]=b['data'][r][c] if b['data'] else 0
                offset_c+=cs[j]
            offset_r+=rs[i]
        # Direct triple sum, independent of typed block multiplication.
        cube=[[sum(dense[i][k]*dense[k][q]*dense[q][j] for k in range(n) for q in range(n)) for j in range(n)] for i in range(n)];out=[];rr=0
        for h in rs:
            line=[];cc=0
            for w in cs:
                data=[row[cc:cc+w] for row in cube[rr:rr+h]];line.append(dict(rows=h,cols=w,data=data if any(x!=0 for row in data for x in row) else None));cc+=w
            out.append(line);rr+=h
        return dict(layout=dict(row_sizes=rs,col_sizes=cs),blocks=out)
    if kind=='choice_exists':return [dict(id=e['id'],label=e['name']) for e in p['entities'] if e['active'] and any(r['entity']==e['id'] and r['funny'] and r['weight']>=p['minimum'] for r in p['relations'])]
    if kind=='moderation_ids':
        # Keep each post's creation sequence and resolve its topic through merge links.
        posts=copy.deepcopy(p['queue']);queued={x['id'] for x in posts};links={};topics=set(p['topics'])
        for e in p['events']:
            if e['kind']=='merge':
                for s in e['sources']:links[s]=e['target'];topics.remove(s)
            elif e['kind']=='post':
                posts.append({k:e[k] for k in ['id','tid','user']})
                if not set(p['memberships'][e['user']])&set(p['exempt_groups']):queued.add(e['id'])
            else:queued.remove(e['id'])
        for post in posts:
            while post['tid'] in links:post['tid']=links[post['tid']]
        return dict(topics=sorted(topics),queue=sorted([x for x in posts if x['id'] in queued],key=lambda x:x['id']),published=sorted([x for x in posts if x['id'] not in queued],key=lambda x:x['id']))
    from oracles_final import final_expected
    return final_expected(kind,p)
