def compute(p):
 todo={t['id']:set(t['needs']) for t in p['tasks']};done=set();out=[]
 while todo:
  wave=sorted(k for k,v in todo.items() if v<=done)
  if not wave:raise ValueError('cyclic task dependency')
  out.append(wave);done.update(wave)
  for k in wave:del todo[k]
 return out
