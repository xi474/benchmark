from fractions import Fraction
def compute(p):
    def prep(course):
        by={item:(label,[Fraction(str(x)) for x in grades if x is not None]) for item,label,grades in course['items']}
        reach={item:set() for item in by}
        for a,b in course['edges']:reach[a].add(b)
        for mid in by:
            for a in by:
                if mid in reach[a]:reach[a].update(reach[mid])
        return [(item,label,sum(scores),len(scores)) for item,(label,scores) in sorted(by.items()) if scores],reach

    result={}
    for k,v in p['courses'].items():
        rows,reach=prep(v)
        result[k]=[[[item,label,[score.numerator,score.denominator],n] for item,label,score,n in rows],{i:sorted(x) for i,x in reach.items()}]
    return result
