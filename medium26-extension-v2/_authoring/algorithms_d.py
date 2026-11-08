from common import *
from algorithms_a import files
import csv, datetime, io, xml.etree.ElementTree as ET
from decimal import Decimal

@operation('marc_xml_records', '''输入{xml:str,language_codes:[唯一三字母小写代码]}。只接受MARC XML的collection或record根（可带标准namespace），禁DOCTYPE/ENTITY。每record含唯一controlfield tag=001作为非空ID；controlfield tag为3位数字，同tag不重复，保留原文本（008依赖固定列）；datafield tag为3位数字，subfield code为一个字母或数字，保留子字段顺序和文本。未知XML元素/坏XML/重复记录ID报错。返回{records:[{id,controls:{tag:text},fields:[{tag,subfields:[{code,value}]}]}]}按id。不支持二进制MARC。''')
def marc_xml_records(p,c):
    d=raw(p); xml=string(d,'xml',True); require('<!DOCTYPE' not in xml.upper() and '<!ENTITY' not in xml.upper())
    try:root=ET.fromstring(xml)
    except ET.ParseError as e:raise ValueError('bad MARC XML') from e
    def local(e):return e.tag.rsplit('}',1)[-1]
    require(local(root) in ('collection','record')); records=list(root) if local(root)=='collection' else [root]; out=[]
    for record in records:
        require(local(record)=='record'); controls={}; fields=[]
        for item in record:
            tag=item.attrib.get('tag',''); require(re.fullmatch(r'\d{3}',tag) is not None)
            if local(item)=='controlfield':require(tag not in controls and len(item)==0); controls[tag]=item.text or ''
            else:
                require(local(item)=='datafield'); sub=[]
                for x in item:require(local(x)=='subfield' and re.fullmatch(r'[A-Za-z0-9]',x.attrib.get('code','')) is not None and len(x)==0); sub.append(dict(code=x.attrib['code'],value=x.text or ''))
                fields.append(dict(tag=tag,subfields=sub))
        require('001' in controls); out.append(dict(id=text(controls['001']),controls=controls,fields=fields))
    return dict(records=sorted(unique(out),key=lambda x:x['id']))
def subfields(f,code):return [x['value'] for x in rows(f,'subfields') if x['code']==code]
def heading(f,codes):return ' '.join(' '.join(x['value'].split()) for x in rows(f,'subfields') if x['code'] in codes).strip(' /,:;')
def link(f):
    values=subfields(f,'6'); require(len(values)<=1)
    if not values:return None
    m=re.fullmatch(r'(\d{3})-(\d{2})(?:/.*)?',values[0]); require(m is not None); return m[1],m[2]
@operation('marc_names_titles', '''输入为marc_xml_records结果。每条100用$a/$b连接作者名，245用$a/$b连接标题；词内空白折叠，首尾空格/斜线/逗号/冒号/分号移除，句点保留。100/245的$6必须为880-NN，880的$6为100-NN或245-NN（允许/后缀）；只有tag和NN双向匹配才增加替代文字，孤立880忽略。返回{records:[{id,authors:[{name,alternates:[去重排序]}],titles:[{title,alternates}]}]}，record按id，基础字段保持原顺序。''')
def marc_names_titles(p,c):
    out=[]
    for r in rows(raw(p),'records'):
        fs=rows(r,'fields'); authors=[]; titles=[]
        for f in fs:
            if f['tag'] not in ('100','245'):continue
            key=link(f)
            if key:require(key[0]=='880')
            value=heading(f,{'a','b'}); alternatives=[]
            if key:
                for alt in fs:
                    if alt['tag']=='880' and link(alt)==(f['tag'],key[1]):alternatives.append(heading(alt,{'a','b'}))
            target=authors if f['tag']=='100' else titles; target.append({('name' if f['tag']=='100' else 'title'):value,'alternates':sorted(set(alternatives))})
        out.append(dict(id=r['id'],authors=authors,titles=titles))
    return dict(records=out)
@operation('marc_languages', '''输入依次为原输入、marc_xml_records。language_codes限定有效代码，必须3个小写字母。008存在时长度>=38，从下标35..37取一个代码；041的$a/$d/$h字符串去首尾空白后按每3字符切分，长度非3倍数报错。有效代码去重排序，未知代码忽略。返回{records:[{id,languages:[代码]}]}。不能把gerlat当一个代码。''')
def marc_languages(p,c):
    d=raw(p); codes=rows(d,'language_codes'); require(len(codes)==len(set(codes)) and all(type(x) is str and re.fullmatch(r'[a-z]{3}',x) for x in codes)); allowed=set(codes); out=[]
    for r in rows(raw(p,1),'records'):
        values=[]; controls=obj(field(r,'controls'))
        if '008' in controls:require(len(controls['008'])>=38); values.append(controls['008'][35:38])
        for f in rows(r,'fields'):
            if f['tag']=='041':
                for x in f['subfields']:
                    if x['code'] in ('a','d','h'):
                        v=x['value'].strip(); require(len(v)%3==0); values.extend(v[i:i+3] for i in range(0,len(v),3))
        out.append(dict(id=r['id'],languages=sorted(set(values)&allowed)))
    return dict(records=out)
@operation('marc_subjects', '''输入为marc_xml_records。处理600/610/611/630/650/651，分别归people/organizations/meetings/works/topics/places。每字段$a/$b先连接为主标题，其$v/$x/$y/$z按出现顺序以" -- "连接为细分；每段空白折叠并剥首尾空格/斜线/逗号/冒号/分号，保留句点。同类型相同完整标题按字段出现次数计数，不按子字段数重复计。返回{records:[{id,subjects:{六类各自:[{value,count}]按value}}]}，无字段为空列表。''')
def marc_subjects(p,c):
    kinds={'600':'people','610':'organizations','611':'meetings','630':'works','650':'topics','651':'places'}; out=[]
    for r in rows(raw(p),'records'):
        counts={x:{} for x in kinds.values()}
        for f in rows(r,'fields'):
            if f['tag'] not in kinds:continue
            parts=[heading(f,{'a','b'})]+[' '.join(x['value'].split()).strip(' /,:;') for x in f['subfields'] if x['code'] in ('v','x','y','z')]; value=' -- '.join(x for x in parts if x)
            if value:
                by=counts[kinds[f['tag']]]; by[value]=by.get(value,0)+1
        out.append(dict(id=r['id'],subjects={k:[dict(value=v,count=n) for v,n in sorted(vals.items())] for k,vals in counts.items()}))
    return dict(records=out)
@operation('marc_catalog', '''输入依次marc_names_titles、marc_languages、marc_subjects。三路记录ID集合必须完全相同且各路唯一；按id连接所有语义字段，返回{records:[{id,authors,titles,languages,subjects}],record_count}。不能按行号zip，不能丢缺少语言/主题的书目。''')
def marc_catalog(p,c):
    maps=[{x['id']:x for x in unique(rows(raw(p,i),'records'))} for i in range(3)]; require(set(maps[0])==set(maps[1])==set(maps[2])); out=[]
    for id_ in sorted(maps[0]):out.append({**maps[0][id_],**maps[1][id_],**maps[2][id_]})
    return dict(records=out,record_count=len(out))
def f22(s):
    xml='<collection xmlns="http://www.loc.gov/MARC21/slim">'
    for i in range(4):
        xml+=f'<record><controlfield tag="001">book{s}-{i}</controlfield><controlfield tag="008">'+(' '*35)+'eng  </controlfield><datafield tag="100"><subfield code="6">880-01</subfield><subfield code="a">Author</subfield></datafield><datafield tag="880"><subfield code="6">100-01</subfield><subfield code="a">作者</subfield></datafield><datafield tag="245"><subfield code="a">Example :</subfield><subfield code="b">subtitle /</subfield></datafield><datafield tag="041"><subfield code="a">gerlat</subfield></datafield>'
        xml+='<datafield tag="610"><subfield code="a">Jesuits.</subfield><subfield code="b">Dept.</subfield></datafield>'*2+'</record>'
    return dict(xml=xml+'</collection>',language_codes=['eng','ger','lat','fra'])
task('MP22','marc_catalog_import','multistage4',[('domains/reader',component('reader','marc_xml_records')),('domains/names',component('names','marc_names_titles',[output('reader')])),('domains/languages',component('languages','marc_languages',['inputs/case.json',output('reader')])),('domains/subjects',component('subjects','marc_subjects',[output('reader')])),('views/catalog',component('catalog','marc_catalog',[output('names'),output('languages'),output('subjects')]))],f22)

@operation('reshard_chunks', '''输入{files:[{path,hex}],max_file_bytes:int>=16,max_entries:int>=2}。原文件路径安全且唯一。按path排序，将每文件原字节顺序切成最多max_file_bytes的块；全球块编号从0起为d000000.bin（至少6位十进制）。空文件无块。返回{chunks:[{name,hex}],manifest:{files:[{path,size,sha256,parts:[块名按序]}]}}。保留空文件、空行、无末尾换行和任意字节，不做strip/压缩/最优装箱。''')
def reshard_chunks(p,c):
    d=raw(p); fs=files(d); cap=ints(d,'max_file_bytes',16); ints(d,'max_entries',2); chunks=[]; entries=[]
    for path,hx in sorted(fs.items()):
        data=bytes.fromhex(hx); parts=[]
        for start in range(0,len(data),cap):
            name=f'd{len(chunks):06d}.bin'; chunks.append(dict(name=name,hex=data[start:start+cap].hex())); parts.append(name)
        entries.append(dict(path=path,size=len(data),sha256=hashlib.sha256(data).hexdigest(),parts=parts))
    return dict(chunks=chunks,manifest=dict(files=entries))
@operation('reshard_layout', '''输入依次原输入、reshard_chunks。manifest紧凑规范JSON的UTF8字节也切成max_file_bytes大小，命名m000000.bin起，元数据同样受大小上限限制。数据块与元数据块按name字典序排序，共N项；取最小h>=1使max_entries**h>=N。每项序号i转成恰h位max_entries进制，前h-1位各作为目录n<数字>，末位不入路径，文件名仍原name。返回{tree:[{path,hex}]按path,max_entries,max_file_bytes}；这样每层直接目录项数（文件+子目录）均受限。索引不放在超大单独JSON文件，layout对象只是文件树快照。''')
def reshard_layout(p,c):
    d=raw(p); plan=raw(p,1); cap=ints(d,'max_file_bytes',16); fan=ints(d,'max_entries',2); meta=canonical(obj(field(plan,'manifest'))).encode(); entries=rows(plan,'chunks')[:]+[dict(name=f'm{i//cap:06d}.bin',hex=meta[i:i+cap].hex()) for i in range(0,len(meta),cap)]; entries.sort(key=lambda x:x['name']); h=1
    while fan**h<len(entries):h+=1
    tree=[]
    for i,r in enumerate(entries):
        digits=[]; n=i
        for _ in range(h):digits.append(n%fan);n//=fan
        digits.reverse(); path='/'.join(['n'+str(x) for x in digits[:-1]]+[r['name']]); tree.append(dict(path=path,hex=r['hex']))
    return dict(tree=sorted(tree,key=lambda x:x['path']),max_entries=fan,max_file_bytes=cap)
@operation('reshard_restore', '''唯一输入为reshard_layout文件树。验证每文件<=max_file_bytes、每目录直接项（文件+子目录）<=max_entries、无文件/目录重名，路径安全且basename唯一。所有basename必须m数字.bin或d数字.bin，m块从000000连续编号，连接后解析manifest。按manifest.files顺序还原parts；原path唯一安全，每个d块须恰被引用一次，size和原字节sha256相符；缺块、重复引用、额外数据块或摘要不符报ValueError。返回{files:[{path,hex}]按path,total_bytes}。不读取原输入当作恢复答案。''')
def reshard_restore(p,c):
    d=raw(p); cap=ints(d,'max_file_bytes',16); fan=ints(d,'max_entries',2); tree=unique(rows(d,'tree'),'path'); by={}; directory={}; paths=set()
    for r in tree:
        path=safe_path(r['path']); data=bytes.fromhex(string(r,'hex',True)); require(len(data)<=cap); name=PurePosixPath(path).name; require(name not in by and re.fullmatch(r'[md]\d{6,}\.bin',name)); by[name]=data; paths.add(path)
        bits=path.split('/')
        for i,bit in enumerate(bits):directory.setdefault('/'.join(bits[:i]),set()).add(bit)
    for directory_path,entries in directory.items():require(len(entries)<=fan);require(not directory_path or directory_path not in paths,'file/dir collision')
    names=sorted(x for x in by if x.startswith('m')); require(names==[f'm{i:06d}.bin' for i in range(len(names))] and names)
    manifest=obj(json.loads(b''.join(by[x] for x in names).decode('utf-8'))); out=[]; used=set()
    for r in unique(rows(manifest,'files'),'path'):
        path=safe_path(r['path']); parts=rows(r,'parts'); require(all(type(x) is str and x.startswith('d') and x in by and x not in used for x in parts) and len(parts)==len(set(parts))); used.update(parts); data=b''.join(by[x] for x in parts); require(len(data)==ints(r,'size',0) and hashlib.sha256(data).hexdigest()==string(r,'sha256')); out.append(dict(path=path,hex=data.hex()))
    require(used=={x for x in by if x.startswith('d')}); return dict(files=sorted(out,key=lambda x:x['path']),total_bytes=sum(len(bytes.fromhex(x['hex'])) for x in out))
def f23(s):return dict(files=[dict(path=f'dir{i}/file.txt',hex=(b'\n\n' if i==0 else b'' if i==1 else (f'line {s}-{i}\n'.encode()*i+b'no-final-newline')).hex()) for i in range(8)],max_file_bytes=32+s%3*16,max_entries=2+s%3)
task('MP23','reversible_file_resharding','linux2',[('products/chunks',component('chunks','reshard_chunks')),('products/layout',component('layout','reshard_layout',['inputs/case.json',output('chunks')])),('products/restore',component('restore','reshard_restore',[output('layout')]))],f23)

def departments(d):
    ds={x['id']:x for x in unique(rows(d,'departments'))}
    for x in ds.values():string(x,'country')
    for x in unique(rows(d,'professors')): require(set(rows(x,'departments'))<=ds.keys())
    return ds
@operation('eu_professors', '输入{departments:[{id,country}],professors:[{id,departments:[部门ID]}],students:[{id,enrolments:[{department,start:ISO日期,end:ISO日期或null}]}],as_of:ISO日期,eu:[国家代码]}。教授部门引用存在，重复任职引用按集合。只要至少一个任职部门country在给定eu中即合格；返回{ids:[合格教授ID排序]}。EU口径不从系统时钟或网络推断。professors是数据准备阶段已预筛为正式教授的名单；本API不接收混合职称候选、不实现职称筛选，也不从id推断职称。其余三个组件继承此输入范围。')
def eu_professors(p,c):
    d=raw(p); ds=departments(d); eu=set(rows(d,'eu')); [text(x) for x in eu]; return dict(ids=sorted(x['id'] for x in d['professors'] if any(ds[k]['country'] in eu for k in x['departments'])))
@operation('department_students', '''输入同eu_professors。start<=as_of且(end=null或as_of<end)才为在读，end非null时须>start；逐department以student.id做DISTINCT，重复入学记录不多计。同一学生在多个部门可分别计数，不能先跨部门并集。返回{counts:{全部部门ID:在读人数}}。日期以YYYY-MM-DD固定，不含时区。''')
def department_students(p,c):
    d=raw(p); ds=departments(d); day=datetime.date.fromisoformat(string(d,'as_of')); sets={k:set() for k in ds}
    for student in unique(rows(d,'students')):
        for e in rows(student,'enrolments'):
            dept=string(e,'department'); require(dept in ds); start=datetime.date.fromisoformat(string(e,'start')); end=datetime.date.fromisoformat(e['end']) if field(e,'end') is not None else None; require(end is None or end>start)
            if start<=day and (end is None or day<end):sets[dept].add(student['id'])
    return dict(counts={k:len(v) for k,v in sets.items()})
@operation('employment_countries', '''输入同eu_professors。返回{countries:{教授ID:全部任职国家去重排序}}，包括EU之外任职，不只返回使教授合格的国家。教授无任职返回空列表。''')
def employment_countries(p,c):
    d=raw(p); ds=departments(d); return dict(countries={x['id']:sorted({ds[k]['country'] for k in x['departments']}) for x in d['professors']})
@operation('university_query', '''输入依次原输入、eu_professors、department_students、employment_countries。仅返回EU资格合格且至少一个单独任职部门在读人数>10的教授；达到人数部门可不同于EU资格部门。返回{professors:[{id,countries:全部任职国家,eligible_departments:[人数>10部门排序]}]}按id。两个部门各6人不等同于某部门>10。''')
def university_query(p,c):
    d=raw(p); eligible=set(rows(raw(p,1),'ids')); counts=obj(field(raw(p,2),'counts')); countries=obj(field(raw(p,3),'countries')); out=[]
    for x in sorted(rows(d,'professors'),key=lambda r:r['id']):
        ds=sorted(k for k in set(x['departments']) if integer(counts[k],0)>10)
        if x['id'] in eligible and ds:out.append(dict(id=x['id'],countries=countries[x['id']],eligible_departments=ds))
    return dict(professors=out)
def f24(s):
    return dict(departments=[dict(id='a',country='DE'),dict(id='b',country='US'),dict(id='c',country='FR')],professors=[dict(id=f'p{s}',departments=['a','b']),dict(id=f'q{s}',departments=['a','c'])],students=[dict(id=f's{i}',enrolments=[dict(department='a' if i<6 else 'c' if i<12 else 'b',start='2024-01-01',end=None)]) for i in range(24)],as_of='2025-08-16',eu=['DE','FR'])
task('MP24','university_relation_query','reasoning4',[('engines/eu',component('eu','eu_professors')),('engines/students',component('students','department_students')),('engines/countries',component('countries','employment_countries')),('engines/query',component('query','university_query',['inputs/case.json',output('eu'),output('students'),output('countries')]))],f24)

@operation('invoice_classification', '''输入{documents:[{id,filename:安全相对路径,text:str}]}，ID唯一。按不区分大小写的独立英文单词：先有invoice则invoice，否则有receipt则receipt，其余other。返回{classes:{id:类别}}。来源已提供文本，本题不做OCR/PDF解析，不对文件名猜类别。''')
def invoice_classification(p,c):
    out={}
    for d in unique(rows(raw(p),'documents')):
        safe_path(string(d,'filename')); content=string(d,'text',True); out[d['id']]='invoice' if re.search(r'\binvoice\b',content,re.I) else 'receipt' if re.search(r'\breceipt\b',content,re.I) else 'other'
    return dict(classes=out)
@operation('invoice_amounts', '''输入同invoice_classification。按整行（可有首尾空白、不区分大小写）解析"Total: 金额"、"Amount Due: 金额"、"VAT: 金额"。金额仅非负十进制、可标准千分位、必须2位小数，可有USD前缀；同标签重复报ValueError、标签行金额非法报ValueError。Total优先Amount Due，均无则total=null；VAT无则"0.00"。返回{amounts:{id:{total:两位小数字符串或null,vat:两位字符串}}}；不能用float，不能把Amount Due覆盖Total。''')
def invoice_amounts(p,c):
    out={}
    for d in unique(rows(raw(p),'documents')):
        labels={}
        for line in string(d,'text',True).splitlines():
            m=re.fullmatch(r'\s*(Total|Amount Due|VAT)\s*:\s*(.*?)\s*',line,re.I)
            if not m:continue
            label=m[1].lower(); require(label not in labels); value=re.sub(r'^USD\s+','',m[2],flags=re.I); require(re.fullmatch(r'(?:0|[1-9]\d*|[1-9]\d{0,2}(?:,\d{3})+)\.\d{2}',value) is not None); labels[label]=Decimal(value.replace(',',''))
        total=labels.get('total',labels.get('amount due')); out[d['id']]=dict(total=format(total,'.2f') if total is not None else None,vat=format(labels.get('vat',Decimal(0)),'.2f'))
    return dict(amounts=out)
@operation('invoice_archive_summary', '''输入依次原documents、invoice_classification、invoice_amounts。每文档归档路径classified/类别/id/原filename（id须为安全单路径段），保存text原UTF8字节hex；invoice/receipt必须有total，other可无。返回{archives:[{path,hex}]按path,rows:[{id,filename,kind,total,vat}]按id,csv:str,totals:{invoice:两位金额,receipt:两位金额}}。CSV使用标准csv.writer、LF结尾，首行为id,filename,kind,total,vat，null金额写空单元格；totals只累计对应类total，不加VAT。''')
def invoice_archive_summary(p,c):
    docs=unique(rows(raw(p),'documents')); classes=obj(field(raw(p,1),'classes')); amounts=obj(field(raw(p,2),'amounts')); archives=[]; rows_=[]; totals=dict(invoice=Decimal(0),receipt=Decimal(0)); stream=io.StringIO(newline=''); writer=csv.writer(stream,lineterminator='\n'); writer.writerow(['id','filename','kind','total','vat'])
    for d in sorted(docs,key=lambda x:x['id']):
        id_=safe_path(d['id']); require('/' not in id_); path=safe_path(d['filename']); kind=classes[id_]; require(kind in ('invoice','receipt','other')); amount=obj(amounts[id_]); total=amount['total']; vat=amount['vat']
        if kind in totals:require(total is not None); totals[kind]+=Decimal(total)
        r=dict(id=id_,filename=path,kind=kind,total=total,vat=vat); rows_.append(r); archives.append(dict(path='classified/'+kind+'/'+id_+'/'+path,hex=d['text'].encode().hex())); writer.writerow([id_,path,kind,total if total is not None else '',vat])
    return dict(archives=sorted(archives,key=lambda x:x['path']),rows=rows_,csv=stream.getvalue(),totals={k:format(v,'.2f') for k,v in totals.items()})
def f25(s):return dict(documents=[dict(id=f'd{s}-{i}',filename=f'folder/invoice,{i}.txt',text=('Invoice' if i%2 else 'Receipt')+f'\nTotal: USD 1,2{i:02d}.50\nAmount Due: 12.00\n'+('VAT: 0.00\n' if i%3 else '')) for i in range(8)]+[dict(id='other',filename='note.txt',text='Meeting notes\n')])
task('MP25','text_invoice_archive','multistage4',[('domains/classification',component('classification','invoice_classification')),('domains/amounts',component('amounts','invoice_amounts')),('views/archive',component('archive','invoice_archive_summary',['inputs/case.json',output('classification'),output('amounts')]))],f25)

def local_datetime(value):
    text(value); require(re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}',value) is not None); return datetime.datetime.fromisoformat(value)
@operation('dinner_days', '''输入{today:YYYY-MM-DD,events:[{id,start:YYYY-MM-DDTHH:MM,end:同格式,kind:str,attendees:[id]}],contacts:[id]}。日期从today到下一自然周周五（周一为周首），两端包含；例如2026-11-04到2026-11-13。返回{dates:[YYYY-MM-DD按升序]}，固定时区、不等待、不处理RRULE。''')
def dinner_days(p,c):
    day=datetime.date.fromisoformat(string(raw(p),'today')); delta=11-day.weekday(); return dict(dates=[str(day+datetime.timedelta(days=i)) for i in range(delta+1)])
@operation('dinner_calendar_index', '''输入同dinner_days。事件ID唯一，end>start，所有参会人存在于contacts（contacts不重复），kind非空。本地子集将19:00开始的kind=dinner事件限制为当天20:00前结束（含20:00），其他活动可跨日。返回{events:[原事件按id,attendees去重排序],existing_dinners:[start时间恰19:00且kind="dinner"的日期去重排序]}。旧晚餐哪怕只持续10分钟也跳过该日的新增/冲突选择。所有时间须无时区且精确到分钟。''')
def dinner_calendar_index(p,c):
    d=raw(p); people=rows(d,'contacts'); require(len(people)==len(set(people))); [text(x) for x in people]; out=[]; existing=set()
    for e in unique(rows(d,'events')):
        start=local_datetime(string(e,'start')); end=local_datetime(string(e,'end')); require(end>start); kind=string(e,'kind'); attendees=set(rows(e,'attendees')); require(attendees<=set(people)); out.append({**e,'attendees':sorted(attendees)})
        if kind=='dinner' and start.hour==19 and start.minute==0:require(end<=start.replace(hour=20,minute=0),'dinner exceeds bounded hour');existing.add(str(start.date()))
    return dict(events=sorted(out,key=lambda x:x['id']),existing_dinners=sorted(existing))
@operation('dinner_change_plan', '''输入依次dinner_days、dinner_calendar_index。跳过existing_dinners内日期的新增与冲突选择；其他日创建19:00–20:00晚餐提醒，ID="dinner-日期"，kind=dinner,attendees=[]。取消所有与新提醒半开区间相交旧事件，跨日旧事件只取消一次：即使覆盖了跳过日，只要也与未跳过日的新提醒冲突，仍整条取消。恰19点结束不冲突。新ID与任何旧事件冲突报错。返回{added:[新事件按start],cancelled:[原事件ID排序],snapshots:[被取消原事件按id]}。''')
def dinner_change_plan(p,c):
    dates=rows(raw(p),'dates'); index=raw(p,1); events=rows(index,'events'); old={x['id'] for x in events}; existing=set(rows(index,'existing_dinners')); added=[]; cancel=set()
    for day in dates:
        if day in existing:continue
        start=local_datetime(day+'T19:00'); end=start+datetime.timedelta(hours=1); id_='dinner-'+day; require(id_ not in old)
        added.append(dict(id=id_,start=start.isoformat(timespec='minutes'),end=end.isoformat(timespec='minutes'),kind='dinner',attendees=[]))
        for e in events:
            if local_datetime(e['start'])<end and local_datetime(e['end'])>start:cancel.add(e['id'])
    return dict(added=sorted(added,key=lambda x:x['start']),cancelled=sorted(cancel),snapshots=[x for x in events if x['id'] in cancel])
@operation('dinner_notifications', '''输入为dinner_change_plan。从被取消事件快照为每位受影响联系人生成一条通知，返回{outbox:[{to:联系人ID,event_ids:[该人被取消活动ID去重排序]}]}按to；无参会人不发通知。不通知保留活动参会人，不因跨日活动产生重复。''')
def dinner_notifications(p,c):
    by={}
    for e in rows(raw(p),'snapshots'):
        for person in rows(e,'attendees'):by.setdefault(person,set()).add(e['id'])
    return dict(outbox=[dict(to=k,event_ids=sorted(v)) for k,v in sorted(by.items())])
@operation('dinner_apply', '''输入依次dinner_calendar_index、dinner_change_plan、dinner_notifications。将cancelled从旧events删除，再加入added，输出{events:[最终事件按id],outbox:上游通知}。未涉及旧事件原样保留；重复运行同today和新events应无新增/取消/通知，这是有限状态幂等，不是真实日历调用。''')
def dinner_apply(p,c):
    index=raw(p); plan=raw(p,1); return dict(events=sorted([x for x in rows(index,'events') if x['id'] not in set(rows(plan,'cancelled'))]+rows(plan,'added'),key=lambda x:x['id']),outbox=rows(raw(p,2),'outbox'))
def f26(s):return dict(today='2026-11-04',contacts=['a','b'],events=[dict(id='existing',start='2026-11-05T19:00',end='2026-11-05T19:10',kind='dinner',attendees=['a']),dict(id=f'conflict{s}',start='2026-11-06T18:30',end='2026-11-07T20:30',kind='other',attendees=['b','a','a']),dict(id='edge',start='2026-11-04T18:00',end='2026-11-04T19:00',kind='other',attendees=['a'])])
task('MP26','recurring_dinner_calendar','reasoning4',[('engines/dates',component('dates','dinner_days')),('engines/calendar',component('calendar','dinner_calendar_index')),('engines/plan',component('plan','dinner_change_plan',[output('dates'),output('calendar')])),('engines/notifications',component('notifications','dinner_notifications',[output('plan')])),('engines/apply',component('apply','dinner_apply',[output('calendar'),output('plan'),output('notifications')]))],f26)
