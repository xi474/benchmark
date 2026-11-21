def compute(p):
 out=[]
 for t in p['topics']:
  row={}
  for paper in p['papers']:
   vs=[q for topic,section,q in paper['claims'] if topic==t and section in paper['methods']]
   if vs:row[paper['id']]=max(vs)
  out.append(row)
 return out
