def connectivity(q,t):
    assets={a['id']:a for a in q['assets']};result={}
    def active(k):
        if k not in result:
            a=assets[k];result[k]=t>=a['repair_at'] and (a['parent'] is None or active(a['parent']))
        return result[k]
    return {k:active(k) for k in assets}

def replay(q,policy):
    if len(policy)!=q['periods']:raise ValueError('one policy per period')
    battery={a['id']:a['battery_initial'] for a in q['assets']};on={k:False for k in battery};locked={k:0 for k in battery};periods=[];cost=0
    for t,allocation in enumerate(policy):
        if set(allocation)!=set(battery):raise ValueError('missing asset')
        connected=connectivity(q,t);rows=[];grid_total=ports=0
        for a in q['assets']:
            k=a['id'];u,g,d=allocation[k];before=battery[k];solar=a['solar'][t];demand=a['demand'][t];used=min(solar,demand);charge=min(a['battery_capacity']-before,solar-used);curtailed=solar-used-charge;residual=demand-used
            if u not in (False,True) or u and not connected[k] or locked[k]>0 and u!=on[k]:raise ValueError('port residency/connection')
            started=bool(u and not on[k]);changed=u!=on[k]
            locked[k]=(a['min_up'] if u else a['min_down'])-1 if changed else max(0,locked[k]-1);on[k]=bool(u)
            if int(g)!=g or int(d)!=d or g<0 or d<0 or g+d>residual or d>a['battery_discharge_limit'] or d>before+charge or g and not u:raise ValueError('energy decision')
            grid_total+=g;ports+=bool(u);cost+=a['startup_cost']*started;battery[k]=before+charge-d;served=used+g+d
            rows.append(dict(id=k,connected=connected[k],port_on=bool(u),started=started,demand=demand,solar=solar,battery_before=before,solar_used=used,solar_charge=charge,solar_curtailed=curtailed,grid_used=g,battery_discharge=d,battery_final=battery[k],served=served,unserved=demand-served))
        if grid_total>q['grid_capacity'][t] or ports>q['grid_ports'][t]:raise ValueError('shared grid/ports')
        periods.append(dict(t=t,assets=rows,grid_unused=q['grid_capacity'][t]-grid_total,grid_active=ports))
    all_rows=[r for p in periods for r in p['assets']];assets={a['id']:a for a in q['assets']}
    summary={k:sum(r[k] for r in all_rows) for k in ['demand','served','unserved','solar_used','solar_curtailed','grid_used']}
    summary.update(weighted_served=sum(assets[r['id']]['priority']*r['served'] for r in all_rows),battery_initial=sum(a['battery_initial'] for a in q['assets']),battery_final=sum(battery.values()),startup_cost=cost)
    assert summary['battery_initial']+sum(r['solar'] for r in all_rows)+summary['grid_used']==summary['served']+summary['battery_final']+summary['solar_curtailed']
    return dict(score=dict(weighted_served=summary['weighted_served'],total_served=summary['served'],startup_cost=cost),periods=periods,summary=summary)

def normalize(ident,value):return {**value,'periods':[{**p,'assets':sorted(p['assets'],key=lambda a:a['id'])} for p in value['periods']]}

def check_value(task,component,actual,expected,request=None):
    try:
        q=request.get('request',request)
        if set(actual)!=set(expected) or actual['score']!=expected['score'] or [p['t'] for p in actual['periods']]!=list(range(q['periods'])):return False
        policy=[]
        for p in actual['periods']:
            allocation={r['id']:(r['port_on'],r['grid_used'],r['battery_discharge']) for r in p['assets']}
            if len(allocation)!=len(p['assets']):return False
            policy.append(allocation)
        return normalize(task,actual)==normalize(task,replay(q,policy))
    except (TypeError,ValueError,KeyError,AttributeError,IndexError):return False
