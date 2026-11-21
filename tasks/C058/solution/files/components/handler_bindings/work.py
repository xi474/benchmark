def compute(p):
 ranks={v:i for i,v in enumerate(p.get('handlers',[]))};bindings={}
 def walk(nodes,prefix):
  for i,node in enumerate(nodes):
   path=prefix+[i]
   if 'block' in node:
    for j,key in enumerate(('tasks','rescue','always')):walk(node['block'].get(key,[]),path+[j])
   else:bindings['/'.join(map(str,path))]=sorted(set(node.get('notify',[])),key=ranks.__getitem__)
 for i,phase in enumerate(('pre','roles','includes','tasks','post')):walk(p.get('program',{}).get(phase,[]),[i,0])
 return [ranks,bindings]
