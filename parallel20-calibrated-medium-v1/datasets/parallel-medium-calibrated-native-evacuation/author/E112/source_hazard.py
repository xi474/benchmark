import heapq
def fire_arrival(data):
    grid=data['grid'];h=len(grid);w=len(grid[0]);cost=data['spread_cost'];times={};queue=[]
    for seed in data['fire_seeds']:
        cell=(seed['r'],seed['c']);time=seed['time']
        if grid[cell[0]][cell[1]]=='#':continue
        if cell not in times or time<times[cell]:times[cell]=time;heapq.heappush(queue,(time,*cell))
    while queue:
        time,r,c=heapq.heappop(queue)
        if time!=times[(r,c)]:continue
        for nr,nc in ((r-1,c),(r,c-1),(r,c+1),(r+1,c)):
            if not (0<=nr<h and 0<=nc<w) or grid[nr][nc]=='#':continue
            arrival=time+cost[nr][nc]
            if (nr,nc) not in times or arrival<times[(nr,nc)]:times[(nr,nc)]=arrival;heapq.heappush(queue,(arrival,nr,nc))
    return [[None if grid[r][c]=='#' else times.get((r,c)) for c in range(w)] for r in range(h)]
