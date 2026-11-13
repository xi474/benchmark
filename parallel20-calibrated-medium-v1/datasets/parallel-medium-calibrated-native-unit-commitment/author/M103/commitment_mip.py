def solve(q):
    import numpy as np
    from scipy.optimize import milp,Bounds,LinearConstraint
    from scipy.sparse import coo_matrix
    from semantic import replay
    assets=q['assets'];by_id={a['id']:a for a in assets};variables=[];lower=[];upper=[];rows=[];lo=[];hi=[];v={}
    def var(key,maximum,minimum=0):v[key]=len(variables);variables.append(key);lower.append(minimum);upper.append(maximum);return v[key]
    def add(row,low=-np.inf,high=np.inf):rows.append(row);lo.append(low);hi.append(high)
    def connected(a,t):
        while True:
            if a['repair_at']>t:return False
            if a['parent'] is None:return True
            a=by_id[a['parent']]
    max_cost=q['periods']*sum(a['startup_cost'] for a in assets);scale2=max_cost+1;scale1=(sum(sum(a['demand']) for a in assets)+1)*scale2;coeff={};constant=0
    for a in assets:
        k=a['id'];cap=a['battery_capacity']
        for t in range(q['periods']):
            used=min(a['demand'][t],a['solar'][t]);surplus=a['solar'][t]-used;residual=a['demand'][t]-used;big=cap+surplus
            before=var(('before',k,t),a['battery_initial'] if t==0 else cap,a['battery_initial'] if t==0 else 0);after=var(('after',k,t),cap)
            charge=var(('charge',k,t),min(surplus,cap));g=var(('grid',k,t),residual);d=var(('discharge',k,t),min(a['battery_discharge_limit'],residual,cap));on=var(('on',k,t),int(connected(a,t)));branch=var(('min-branch',k,t),1)
            start=var(('start',k,t),1);stop=var(('stop',k,t),1)
            if t:add({before:1,v['after',k,t-1]:-1},0,0)
            transition={on:1,start:-1,stop:1}
            if t:transition[v['on',k,t-1]]=-1
            add(transition,0,0);add({start:1,stop:1},high=1)
            add({charge:1,before:1},high=cap);add({charge:1,before:1,branch:-big},low=cap-big);add({charge:1,branch:big},low=surplus)
            add({after:1,before:-1,charge:-1,d:1},0,0);add({g:1,d:1},high=residual);add({g:1,on:-residual},high=0)
            coeff[g]=coeff[d]=-(a['priority']*scale1+scale2);coeff[start]=a['startup_cost'];constant+=used*(a['priority']*scale1+scale2)
        for t in range(q['periods']):
            for tau in range(t,min(q['periods'],t+a['min_up'])):add({v['on',k,tau]:1,v['start',k,t]:-1},low=0)
            for tau in range(t,min(q['periods'],t+a['min_down'])):add({v['on',k,tau]:1,v['stop',k,t]:1},high=1)
    for t in range(q['periods']):
        add({v['grid',a['id'],t]:1 for a in assets},high=q['grid_capacity'][t]);add({v['on',a['id'],t]:1 for a in assets},high=q['grid_ports'][t])
    rr=[];cc=[];vv=[]
    for i,row in enumerate(rows):
        for j,z in row.items():rr.append(i);cc.append(j);vv.append(z)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(rows),len(variables))).tocsc();objective=np.zeros(len(variables))
    for j,z in coeff.items():objective[j]=z
    result=milp(objective,integrality=np.ones(len(variables)),bounds=Bounds(lower,upper),constraints=LinearConstraint(matrix,lo,hi),options={'mip_rel_gap':0,'time_limit':60})
    assert result.success and result.mip_gap==0,result.message
    policy=[{a['id']:(bool(round(result.x[v['on',a['id'],t]])),round(result.x[v['grid',a['id'],t]]),round(result.x[v['discharge',a['id'],t]])) for a in assets} for t in range(q['periods'])]
    answer=replay(q,policy);s=answer['score'];assert s['weighted_served']*scale1+s['total_served']*scale2-s['startup_cost']==constant-round(result.fun)
    return answer
