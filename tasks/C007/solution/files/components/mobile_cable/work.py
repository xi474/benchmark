import re
from datetime import datetime
def canonical(record):
 source=record['source'];v=record['fields']
 if source=='mobile':first,last=v['first'],v['last'];dob=datetime.strptime(v['dob'],'%Y-%m-%d').date().isoformat();ssn=v['ssn'];mail=v['email'];phone=v['phone'];address=v['address']
 elif source=='internet':first,last=v['full_name'].split(' ',1);dob=datetime.strptime(v['birth_date'],'%m/%d/%Y').date().isoformat();ssn='';mail=v['mail'];phone=v['tel'];address=v['street']
 elif source=='cable':last,first=v['last_first'].split(',',1);dob=datetime.strptime(v['birth'],'%Y%m%d').date().isoformat();ssn=v['government_id'];mail=v['contact'];phone=v['phone'];address=v['location']
 else:first,last=v['customer'].split(' ',1);dob=datetime.strptime(v['date_of_birth'],'%d %b %Y').date().isoformat();ssn='';mail=v['email'];phone=v['telephone'];address=v['address']
 letters=lambda s:re.sub('[^a-z0-9]','',s.lower())
 return dict(id=record['id'],first=letters(first),last=letters(last),dob=dob,ssn=re.sub('[^0-9]','',ssn),mail=letters(mail),phone=re.sub('[^0-9]','',phone),address=letters(address))
def compute(p):
 return [[i,canonical(r)] for i,r in enumerate(p['records']) if r['source'] in ('mobile', 'cable')]
