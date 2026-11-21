from collections import defaultdict
def compute(p):
 values=defaultdict(list)
 for student,course,v in p['grades']:
  if course in (1,2) and v is not None:values[student].append(v)
 return {k:sum(v)*100//len(v) for k,v in values.items()}
