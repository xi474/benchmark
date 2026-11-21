def compute(p):
 def visit(host,nodes,path,out):
  for i,node in enumerate(nodes):
   at=path+[i];out['/'.join(map(str,at))]=[node.get('only') is None or host in node['only'],host in node.get('fail_hosts',[])]
   if 'block' in node:
    for j,key in enumerate(('tasks','rescue','always')):visit(host,node['block'].get(key,[]),at+[j],out)
 result={}
 for h in p['hosts']:
  result[h]={}
  for i,k in enumerate(('pre','roles','includes','tasks','post')):visit(h,p.get('program',{}).get(k,[]),[i,0],result[h])
 return result
