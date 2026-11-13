from collections import defaultdict


def fire_relax(q):
    cells=[(r,c) for r,row in enumerate(q['grid']) for c,s in enumerate(row) if s!='#'];dist={p:None for p in cells}
    for s in q['fire_seeds']:
        p=s['r'],s['c']
        if p in dist and (dist[p] is None or s['time']<dist[p]):dist[p]=s['time']
    for _ in cells:
        changed=False
        for u in cells:
            if dist[u] is None:continue
            r,c=u
            for v in [(r-1,c),(r+1,c),(r,c-1),(r,c+1)]:
                if v in dist:
                    value=dist[u]+q['spread_cost'][v[0]][v[1]]
                    if dist[v] is None or value<dist[v]:dist[v]=value;changed=True
        if not changed:break
    return [[dist.get((r,c)) for c in range(len(q['grid'][0]))] for r in range(len(q['grid']))]


def solve(q):
    import numpy as np
    from scipy.optimize import milp,Bounds,LinearConstraint
    from scipy.sparse import coo_matrix
    from semantic import report
    fire=fire_relax(q);horizon=q['max_ticks'];variables=[];objective=[];upper=[];conservation=defaultdict(dict);occupancy=defaultdict(dict);swaps=defaultdict(dict);shelter_rows=defaultdict(dict);nodes={};sources={}
    def safe(p,t):
        r,c=p
        return q['grid'][r][c]!='#' and (fire[r][c] is None or t<fire[r][c]) and not any(e['r']==r and e['c']==c and e['start']<=t<=e['end'] for e in q['closures'])
    cells=[(r,c) for r,row in enumerate(q['grid']) for c,s in enumerate(row) if s!='#'];scale=len(q['evacuees'])*horizon+1
    def add(data,cost=0,ub=1):
        i=len(variables);variables.append(data);objective.append(cost);upper.append(ub);return i
    for e in q['evacuees']:
        name=e['id'];start=(e['r'],e['c']);release=e['release'];available={(t,p) for t in range(release,horizon+1) for p in cells if safe(p,t)};nodes[name]=available
        y=add(('source',name),ub=int((release,start) in available));sources[name]=y
        if (release,start) in available:conservation[name,release,start][y]=-1
        else:conservation[name,'invalid',start][y]=1
        for t,u in available:
            if t<horizon:
                r,c=u
                for v in [u,(r-1,c),(r+1,c),(r,c-1),(r,c+1)]:
                    if (t+1,v) not in available:continue
                    j=add(('move',name,t,u,v));conservation[name,t,u][j]=1;conservation[name,t+1,v][j]=-1;occupancy[t,u][j]=1
                    if u!=v:swaps[t,tuple(sorted((u,v)))][j]=1
            for s in q['shelters']:
                if s['id'] in e['eligible_shelters'] and (s['r'],s['c'])==u and s['opens']<=t<s['closes']:
                    j=add(('end',name,t,u,s['id']),t-scale);conservation[name,t,u][j]=1;occupancy[t,u][j]=1;shelter_rows[s['id']][j]=1
    rows=list(conservation.values())+list(occupancy.values())+list(swaps.values())+[shelter_rows[s['id']] for s in q['shelters']]
    lo=[0]*len(conservation)+[-np.inf]*(len(rows)-len(conservation));hi=[0]*len(conservation)+[1]*(len(occupancy)+len(swaps))+[s['capacity'] for s in q['shelters']]
    rr=[];cc=[];values=[]
    for i,row in enumerate(rows):
        for j,value in row.items():rr.append(i);cc.append(j);values.append(value)
    matrix=coo_matrix((values,(rr,cc)),shape=(len(rows),len(variables))).tocsc()
    result=milp(np.array(objective,dtype=float),integrality=np.ones(len(variables)),bounds=Bounds(np.zeros(len(variables)),np.array(upper)),constraints=LinearConstraint(matrix,lo,hi),options={'mip_rel_gap':0,'time_limit':60})
    assert result.success and result.mip_gap==0,result.message
    selected=[v for v,x in zip(variables,result.x) if x>.5];outgoing={};plans={}
    for v in selected:
        if v[0]!='source':outgoing[v[1],v[2],v[3]]=v
    for e in q['evacuees']:
        if result.x[sources[e['id']]]<.5:continue
        t=e['release'];u=e['r'],e['c'];path=[list(u)]
        while True:
            step=outgoing[e['id'],t,u]
            if step[0]=='end':plans[e['id']]=dict(shelter=step[4],arrival=t,release=e['release'],path=path);break
            u=step[4];t+=1;path.append(list(u))
    answer=report(q,fire,plans);assert round(result.fun)==answer['total_arrival']-scale*answer['max_saved']
    return answer
