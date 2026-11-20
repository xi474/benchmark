from collections import Counter


def initial(q):return tuple(tuple(s['containers']) for s in q['stacks'])


def group(q,state):
    present={k for row in state for k in row}
    return next((set(g)&present for g in q['retrieval_groups'] if set(g)&present),set())


def step(q,state,time,batch):
    stacks={s['id']:i for i,s in enumerate(q['stacks'])};containers={c['id']:c for c in q['containers']};cranes={c['id']:set(c['reaches']) for c in q['cranes']};links={(e['from'],e['to']) for e in q['links']};current=group(q,state);occupied=set();used=set();cost=0;duration=0;following=[list(row) for row in state];delivered=[]
    if not batch['operations'] or len(batch['operations'])>len(cranes) or batch['start']<time:raise ValueError('invalid wave')
    for op in batch['operations']:
        source=stacks[op['from']];name=op['container'];c=containers[name]
        if not state[source] or state[source][-1]!=name or op['crane'] in used:raise ValueError('not a top container or repeated crane')
        used.add(op['crane']);touched={op['from']}
        if op['kind']=='rehandle':
            target=stacks[op['to']];s=q['stacks'][target]
            if op['from']==op['to'] or (op['from'],op['to']) not in links or len(state[target])>=s['capacity'] or c['hazard'] not in s['allowed_hazards']:raise ValueError('illegal destination')
            touched.add(op['to']);cost+=c['rehandle_cost']
        elif op['kind']=='retrieve':
            if op['to'] is not None or name not in current or batch['start']<c['appointment_tick']:raise ValueError('group/appointment')
        else:raise ValueError('unknown operation')
        if touched&occupied or not touched<=cranes[op['crane']]:raise ValueError('shared stack or unreachable crane')
        occupied|=touched;duration=max(duration,c['handling_ticks']);following[source].pop()
        if op['kind']=='rehandle':following[stacks[op['to']]].append(name)
        else:delivered.append(dict(container=name,tick=batch['start']+c['handling_ticks']))
    return tuple(map(tuple,following)),batch['start']+duration,cost,delivered


def replay(q,batches):
    state=initial(q);time=0;cost=0;delivered=[]
    for batch in batches:
        state,time,added,done=step(q,state,time,batch);cost+=added;delivered+=done
    if any(state):raise ValueError('incomplete retrieval')
    return dict(status='ready',rehandle_cost=cost,finish_time=time,batches=batches,delivered=delivered,stacks=[dict(stack=s['id'],containers=list(row)) for s,row in zip(q['stacks'],state)])


def infeasible(q):return dict(status='infeasible',rehandle_cost=None,finish_time=None,batches=[],delivered=[],stacks=[dict(stack=s['id'],containers=s['containers']) for s in q['stacks']])
def normalize(ident,value):return value


def check_value(task,component,actual,expected,request=None):
    try:
        q=request.get('request',request)
        if set(actual)!=set(expected) or actual['status']!=expected['status']:return False
        if expected['status']=='infeasible':
            wanted=infeasible(q)
            return {k:v for k,v in actual.items() if k!='stacks'}=={k:v for k,v in wanted.items() if k!='stacks'} and sorted(actual['stacks'],key=lambda e:e['stack'])==sorted(wanted['stacks'],key=lambda e:e['stack'])
        rebuilt=replay(q,actual['batches'])
        return (actual['rehandle_cost'],actual['finish_time'])==(expected['rehandle_cost'],expected['finish_time'])==(rebuilt['rehandle_cost'],rebuilt['finish_time']) and sorted(actual['delivered'],key=lambda e:e['container'])==sorted(rebuilt['delivered'],key=lambda e:e['container']) and sorted(actual['stacks'],key=lambda e:e['stack'])==sorted(rebuilt['stacks'],key=lambda e:e['stack'])
    except (TypeError,ValueError,KeyError,AttributeError,IndexError):return False
