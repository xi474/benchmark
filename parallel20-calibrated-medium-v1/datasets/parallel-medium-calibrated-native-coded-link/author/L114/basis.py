def add(base, vector):
    rows=list(base)
    for r in rows:
        vector=min(vector,vector^r)
    if not vector:return base
    rows=[min(r,r^vector) for r in rows]
    return tuple(sorted(rows+[vector],reverse=True))
