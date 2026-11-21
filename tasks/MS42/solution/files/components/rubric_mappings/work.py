from itertools import permutations
def compute(p):
    old=sorted(p['rubrics']);new=sorted({s for vs in p['rubrics'].values() for s in vs})
    maps=[dict(zip(old,perm)) for perm in permutations(new) if all(b in p['rubrics'][a] for a,b in zip(old,perm))]
    full=(1<<len(maps))-1
    permits={(a,b):sum(1<<i for i,m in enumerate(maps) if m[a]==b) for a in old for b in new}
    return [full,{a:{b:permits[a,b] for b in new} for a in old}]
