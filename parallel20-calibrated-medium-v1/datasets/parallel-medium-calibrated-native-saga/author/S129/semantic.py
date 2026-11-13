from itertools import combinations


def initial_state(q):return ('forward',tuple(sorted(q.get('initial_attempts',{}).items())),(),())


def step(q,state,batch):
    phase,raw_counts,raw_success,raw_comp=state;actions={a['id']:a for a in q['actions']};counts=dict(raw_counts);comp=dict(raw_comp)
    success={k for k,c in counts.items() if c and actions[k]['forward'][c-1]}
    if phase=='rollback':success=set(raw_success)
    if not batch or len(set(batch))!=len(batch) or len({actions[k]['resource'] for k in batch})!=len(batch):raise ValueError('batch')
    if phase=='forward':
        if any(k in success or counts.get(k,0)>=len(actions[k]['forward']) or not set(actions[k]['deps'])<=success for k in batch):raise ValueError('forward ready')
        failed=[]
        for k in batch:
            counts[k]=counts.get(k,0)+1
            if actions[k]['forward'][counts[k]-1]:success.add(k)
            elif counts[k]==len(actions[k]['forward']):failed.append(k)
        after=('rollback',tuple(sorted(counts.items())),tuple(sorted(success)),()) if failed else ('forward',tuple(sorted(counts.items())),(),())
        return after,max(actions[k]['forward_time'] for k in batch),sorted(failed)
    done={k for k,c in comp.items() if c and (actions[k]['compensate'][c-1] or c==len(actions[k]['compensate']))}
    if any(k not in success or k in done or any(k in actions[child]['deps'] and child not in done for child in success) for k in batch):raise ValueError('compensation ready')
    for k in batch:comp[k]=comp.get(k,0)+1
    return ('rollback',raw_counts,raw_success,tuple(sorted(comp.items()))),max(actions[k]['compensation_time'] for k in batch),[]


def terminal(q,state):
    phase,raw_counts,raw_success,raw_comp=state;actions={a['id']:a for a in q['actions']};counts=dict(raw_counts);comp=dict(raw_comp)
    if phase=='forward':
        success={k for k,c in counts.items() if c and actions[k]['forward'][c-1]}
        return ('committed',[]) if success==set(actions) else None
    success=set(raw_success);done={k for k,c in comp.items() if c and (actions[k]['compensate'][c-1] or c==len(actions[k]['compensate']))}
    if done!=success:return None
    unresolved=sorted(k for k in done if not actions[k]['compensate'][comp[k]-1])
    return ('rollback_incomplete' if unresolved else 'rolled_back',unresolved)


def all_batches(q,state):
    names=sorted(a['id'] for a in q['actions']);result=[]
    for size in range(1,len(names)+1):
        for batch in combinations(names,size):
            try:next_state,elapsed,failed=step(q,state,batch)
            except ValueError:continue
            result.append((batch,next_state,elapsed,failed))
    return result


def normalize(ident,v):
    return {**v,'forward_batches':[sorted(b) for b in v['forward_batches']],'compensation_batches':[sorted(b) for b in v['compensation_batches']],
        'failed_actions':sorted(v['failed_actions']),'unresolved':sorted(v['unresolved'])}


def check_value(task,component,actual,expected,request=None):
    try:
        q=request.get('request',request);state=initial_state(q);cost=0;failures=[]
        if set(actual)!=set(expected) or actual['minimum_time']!=expected['minimum_time']:return False
        for batch in actual['forward_batches']:
            if state[0]!='forward' or terminal(q,state) is not None:return False
            state,elapsed,failed=step(q,state,batch);cost+=elapsed
            if failed:failures=failed
        for batch in actual['compensation_batches']:
            if state[0]!='rollback' or terminal(q,state) is not None:return False
            state,elapsed,failed=step(q,state,batch);cost+=elapsed
        end=terminal(q,state)
        return end is not None and cost==actual['minimum_time'] and actual['status']==end[0] and sorted(actual['unresolved'])==end[1] and sorted(actual['failed_actions'])==failures
    except (TypeError,ValueError,KeyError,AttributeError,IndexError):return False
