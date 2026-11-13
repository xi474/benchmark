VECTORS=[(dx,dy) for dx in (-1,0,1) for dy in (-1,0,1)]

def fit(samples):
    if not samples:return (0,0,0,0)
    scores=[]
    for dx,dy in VECTORS:
        error=sum(s['weight']*(abs(dx-s['dx'])+abs(dy-s['dy'])) for s in samples)
        scores.append((error,dx,dy))
    scores.sort()
    error,dx,dy=scores[0]
    gap=scores[1][0]-error
    return dx,dy,error,gap

def evaluate(data):
    coast={tuple(p) for p in data['coast']}
    buckets={}
    for sample in data['samples']:
        buckets.setdefault((sample['x'],sample['y']),[]).append(sample)
    field=[];lookup={}
    for y in range(data['height']):
        for x in range(data['width']):
            if (x,y) in coast:continue
            dx,dy,error,gap=fit(buckets.get((x,y),[]))
            field.append(dict(x=x,y=y,dx=dx,dy=dy,error=error,gap=gap))
            lookup[(x,y)]=(dx,dy)
    tracks=[]
    for drifter in sorted(data['drifters'],key=lambda d:d['id']):
        x,y=drifter['start']; path=[[x,y]]; blocked=0
        for _ in range(drifter['steps']):
            dx,dy=lookup[(x,y)]; nx,ny=x+dx,y+dy
            if (nx,ny) not in lookup:blocked+=1
            else:x,y=nx,ny
            path.append([x,y])
        tracks.append(dict(id=drifter['id'],path=path,blocked_steps=blocked))
    return dict(field=field,tracks=tracks)
