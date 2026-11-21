def compute(p):
 nodes=p['nodes'].copy();out=[]
 for scan in p['scans']:
  nodes.update(scan['replace']);rows={}
  for path in scan['finish']:
   root,*rest=path.split('/');node=nodes[p['mounts'][root]]
   for child in rest:node=nodes[node['dirs'][child]]
   ignore=set(node['ignore']);rows[path]=[{k:v for k,v in node['files'].items() if k not in ignore},sorted(set(node['dirs'])-ignore)]
  out.append(rows)
 return out
