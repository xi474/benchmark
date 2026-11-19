from common import *
from algorithms_a import files
import datetime

@operation('photo_classification', '''输入{files:[{path,hex}],photos:[{path,festival}],festivals:[唯一非空str],destination:安全相对目录,recipient:非空str}。photos路径唯一且在files内，每张festival非空。仅选择festival在festivals内的照片，按(festival,path)排序。返回{selected:[{path,festival}],missing:[没有照片的festival排序]}；同一节日可有多张，不能找到一张就停止扫描。''')
def photo_classification(p,c):
    d=raw(p); fs=files(d); festivals=rows(d,'festivals'); require(len(festivals)==len(set(festivals))); [text(x) for x in festivals]; photos=unique(rows(d,'photos'),'path'); selected=[]
    for r in photos:
        require(safe_path(r['path']) in fs); festival=string(r,'festival')
        if festival in festivals:selected.append(dict(path=r['path'],festival=festival))
    return dict(selected=sorted(selected,key=lambda r:(r['festival'],r['path'])),missing=sorted(set(festivals)-{r['festival'] for r in selected}))
@operation('photo_migration', '''输入依次为原照片快照、photo_classification。将selected源路径移动到destination/原路径（保留子路径避免同名覆盖）；目标已存在报ValueError；未选文件不动。返回{moves:[{from,to,festival}],files:[{path,hex}]}，moves按(from,to)、files按path。没有照片不失败；hex字节必须保持不变。''')
def photo_migration(p,c):
    d=raw(p); fs=files(d); dst=safe_path(string(d,'destination')); moves=[]
    for r in rows(raw(p,1),'selected'):
        src=safe_path(r['path']); target=dst+'/'+src; require(src in fs and target not in fs); fs[target]=fs.pop(src); moves.append({'from':src,'to':target,'festival':r['festival']})
    return dict(moves=sorted(moves,key=lambda r:(r['from'],r['to'])),files=[dict(path=k,hex=v) for k,v in sorted(fs.items())])
@operation('photo_outbox', '''输入依次为原快照、photo_classification、photo_migration。输出{to:recipient,attachments:[迁移后路径排序],missing:分类结果missing,message:str}。message无缺失时为"Photos ready"，有缺失为"Missing: "+以", "连接的missing。必须从迁移结果选附件，不引用旧路径；空附件也生成缺失报告。''')
def photo_outbox(p,c):
    d=raw(p); missing=rows(raw(p,1),'missing'); migration=raw(p,2); return dict(to=string(d,'recipient'),attachments=sorted(x['to'] for x in rows(migration,'moves')),missing=missing,message='Missing: '+', '.join(missing) if missing else 'Photos ready')
def f08(s):
    paths=[f'photos/day{i}/img.jpg' for i in range(8)]; return dict(files=[dict(path=x,hex=(x+str(s)).encode().hex()) for x in paths]+[dict(path='notes.txt',hex='00')],photos=[dict(path=x,festival=['spring','summer'][i%2]) for i,x in enumerate(paths)],festivals=['spring','summer','winter'],destination='holiday',recipient=f'friend{s}')
task('MP08','holiday_photo_migration','linux2',[('products/classify',component('classify','photo_classification')),('products/migrate',component('migrate','photo_migration',['inputs/case.json',output('classify')])),('products/outbox',component('outbox','photo_outbox',['inputs/case.json',output('classify'),output('migrate')]))],f08)

@operation('panel_slots', '''输入{now:int,windows:[{id,start:int,end:int}],busy:[{id,start:int,end:int}],duration:int>=1,gap:int>=0,...}，单位分钟，所有区间半开且end>start。从windows并集减去busy并排除now前时间，贪心选最早可容纳duration的首场，再选start>=首场end+gap的最早第二场，两个窗口相接可视为连续。返回{slots:[{start,end}],complete:是否两场}，最多2场。合法无足够时段返回部分结果，不报错。''')
def panel_slots(p,c):
    d=raw(p); now=ints(d,'now'); duration=ints(d,'duration',1); gap=ints(d,'gap',0)
    def intervals(key):
        result=[]
        for x in unique(rows(d,key)):
            a=ints(x,'start'); b=ints(x,'end'); require(a<b); result.append((a,b))
        return result
    windows=intervals('windows'); busy=intervals('busy'); points=sorted({now}|{x for r in windows+busy for x in r}); free=[]
    for a,b in zip(points,points[1:]):
        if a>=now and any(x<=a and b<=y for x,y in windows) and not any(x<b and y>a for x,y in busy):
            if free and free[-1][1]==a:free[-1]=(free[-1][0],b)
            else:free.append((a,b))
    selected=[]; minimum=now
    for a,b in free:
        start=max(a,minimum)
        while start+duration<=b and len(selected)<2:
            selected.append(dict(start=start,end=start+duration)); minimum=start+duration+gap; start=minimum
        if len(selected)==2:break
    return dict(slots=selected,complete=len(selected)==2)
@operation('panel_invitees', '''输入含groups:[{id,members:[非空id]}],invite_groups:[群ID],exclude:[联系人ID]。所选群必须存在，成员集合并集减exclude，返回{members:排序ID,group_id:输入namespace+"-panel"}；namespace非空。允许重复的群引用和成员，未知群报错。''')
def panel_invitees(p,c):
    d=raw(p); gs={x['id']:x for x in unique(rows(d,'groups'))}; names=rows(d,'invite_groups'); require(set(names)<=gs.keys()); members=set()
    for n in names:
        for x in rows(gs[n],'members'):members.add(text(x))
    return dict(members=sorted(members-set(rows(d,'exclude'))),group_id=string(d,'namespace')+'-panel')
@operation('supply_selection', '''输入含products:[{id,category,stock:int>=0,price_cents:int>=0,rating:int>=0}],requirements:[{category,quantity:int>=1}]。每个category仅一条需求，按库存足够筛选，选择rating最大、price_cents最小、id最小商品。返回{items:[{category,id,quantity,total_cents}],unavailable:[category排序]}，items按category。不以售价最大代替评分，不跨商品拼库存。''')
def supply_selection(p,c):
    d=raw(p); products=unique(rows(d,'products')); reqs=unique(rows(d,'requirements'),'category'); out=[]; missing=[]
    for r in products: string(r,'category'); ints(r,'stock',0); ints(r,'price_cents',0); ints(r,'rating',0)
    for r in reqs:
        cat=string(r,'category'); n=ints(r,'quantity',1); choices=[x for x in products if x['category']==cat and x['stock']>=n]
        if not choices:missing.append(cat); continue
        best=min(choices,key=lambda x:(-x['rating'],x['price_cents'],x['id'])); out.append(dict(category=cat,id=best['id'],quantity=n,total_cents=n*best['price_cents']))
    return dict(items=sorted(out,key=lambda x:x['category']),unavailable=sorted(missing))
@operation('panel_commit', '''输入依次为panel_slots、panel_invitees、supply_selection。返回{events:[{id,start,end,members}],notification:null或{group_id,members,event_ids},purchase:物资选择结果}。只有complete=true才生成两场，ID为group_id+"-1"/"-2"；通知引用两场ID，成员读取上游members。无两场时events=[]、notification=null，仍保留独立采购结果。''')
def panel_commit(p,c):
    slots=raw(p); group=raw(p,1); purchase=raw(p,2); events=[]
    if field(slots,'complete'):
        events=[dict(id=group['group_id']+'-'+str(i+1),**s,members=group['members']) for i,s in enumerate(slots['slots'])]
    return dict(events=events,notification=dict(group_id=group['group_id'],members=group['members'],event_ids=[x['id'] for x in events]) if events else None,purchase=purchase)
def f09(s):
    return dict(namespace=f'n{s}',now=30,windows=[dict(id='w1',start=0,end=600),dict(id='w2',start=600,end=1200)],busy=[dict(id='b',start=200,end=300)],duration=180,gap=60,groups=[dict(id='a',members=['one','two']),dict(id='b',members=['two','three'])],invite_groups=['a','b'],exclude=['one'],products=[dict(id=f'p{s}-{i}',category='cups' if i%2 else 'pens',stock=20,price_cents=100+i,rating=i%3) for i in range(12)],requirements=[dict(category='cups',quantity=6),dict(category='pens',quantity=4)])
task('MP09','panel_events_procurement','reasoning4',[('engines/calendar',component('calendar','panel_slots')),('engines/invitees',component('invitees','panel_invitees')),('engines/supplies',component('supplies','supply_selection')),('engines/commit',component('commit','panel_commit',[output('calendar'),output('invitees'),output('supplies')]))],f09)

@operation('dinner_date', '''输入{today:ISO日期,weekday:int0..6(周一0),hour:int0..23,guest_count:int>=1,...}。选严格晚于today的下一个weekday（同星期则+7天），返回{start:"YYYY-MM-DDTHH:00",guest_count}。固定本地时区，不涉夏令时。''')
def dinner_date(p,c):
    d=raw(p); today=datetime.date.fromisoformat(string(d,'today')); weekday=ints(d,'weekday',0); hour=ints(d,'hour',0); require(weekday<7 and hour<24); delta=(weekday-today.weekday())%7 or 7
    return dict(start=f'{today+datetime.timedelta(days=delta)}T{hour:02d}:00',guest_count=ints(d,'guest_count',1))
@operation('recent_contact', '''输入含conversations:[{id,contact_id,ts:int,topic:str}],topic:str。按topic.casefold子串匹配，选ts最大、同ts会话id最小，返回{contact_id,conversation_id}，无匹配两个字段均null。会话ID唯一，不能按联系人名字或列表最后一项猜测。''')
def recent_contact(p,c):
    d=raw(p); needle=string(d,'topic').casefold(); cs=unique(rows(d,'conversations')); selected=[]
    for x in cs:
        string(x,'contact_id'); ints(x,'ts')
        if needle in string(x,'topic',True).casefold():selected.append(x)
    best=min(selected,key=lambda x:(-x['ts'],x['id'])) if selected else None
    return dict(contact_id=best['contact_id'] if best else None,conversation_id=best['id'] if best else None)
@operation('dinner_checkout', '''输入依次为原快照、dinner_date、recent_contact。快照含variants:[{id,kind,attributes:object,stock:int,price_cents:int}],wanted:[{kind,attributes:object}]，kind需求唯一。每种需guest_count份，仅attributes完全相等且库存足够者候选，选最低price_cents再id。返回{items:[{id,kind,quantity}],total_cents,checkout:bool,recipient:contact_id或null,start:上游start,unavailable:[kind]}。必须所有类别齐备且recipient非null才checkout；失败仍返回已选items，未做真实购买。''')
def dinner_checkout(p,c):
    d=raw(p); plan=raw(p,1); who=raw(p,2); n=ints(plan,'guest_count',1); variants=unique(rows(d,'variants')); out=[]; missing=[]; total=0
    for v in variants:string(v,'kind'); obj(field(v,'attributes')); ints(v,'stock',0); ints(v,'price_cents',0)
    for r in unique(rows(d,'wanted'),'kind'):
        kind=string(r,'kind'); attrs=obj(field(r,'attributes')); choices=[x for x in variants if x['kind']==kind and x['attributes']==attrs and x['stock']>=n]
        if not choices:missing.append(kind);continue
        v=min(choices,key=lambda x:(x['price_cents'],x['id'])); out.append(dict(id=v['id'],kind=kind,quantity=n)); total+=n*v['price_cents']
    return dict(items=sorted(out,key=lambda x:x['kind']),total_cents=total,checkout=not missing and who['contact_id'] is not None,recipient=who['contact_id'],start=plan['start'],unavailable=sorted(missing))
def f10(s):
    return dict(today='2026-11-04',weekday=s%7,hour=19,guest_count=6,topic='dinner',conversations=[dict(id=f'chat{i}',contact_id=f'c{s}-{i}',ts=i//2,topic='Dinner' if i%2 else 'Lunch') for i in range(8)],variants=[dict(id=f'v{i}',kind='plate' if i%2 else 'cup',attributes=dict(color='white',size='large' if i%3 else 'small'),stock=10 if i%4 else 2,price_cents=90+i) for i in range(12)],wanted=[dict(kind='plate',attributes=dict(color='white',size='large')),dict(kind='cup',attributes=dict(color='white',size='large'))])
task('MP10','dinner_contact_checkout','context8',[('dinner',component('dinner','dinner_date')),('contact',component('contact','recent_contact')),('shopping',component('shopping','dinner_checkout',['inputs/case.json',output('dinner'),output('contact')]))],f10)

@operation('meeting_cancel_plan', '''输入含events:[{id,start:int,end:int,kind:str,organizer:str,attendees:[id]}],window:[lo,hi],cancel_organizer:str。半开按活动start落入窗口且organizer匹配且kind="meeting"筛选；end>start。返回{cancelled:[id排序],notify:[{event_id,recipients:该活动去重排序参会人}]}。研讨会不因时间/组织者匹配而取消。''')
def meeting_cancel_plan(p,c):
    d=raw(p); lo,hi=rows(d,'window'); integer(lo); integer(hi); require(lo<hi); org=string(d,'cancel_organizer'); selected=[]
    for e in unique(rows(d,'events')):
        start=ints(e,'start'); require(ints(e,'end')>start); string(e,'kind'); string(e,'organizer'); [text(x) for x in rows(e,'attendees')]
        if lo<=start<hi and e['kind']=='meeting' and e['organizer']==org:selected.append(e)
    selected.sort(key=lambda x:x['id']); return dict(cancelled=[x['id'] for x in selected],notify=[dict(event_id=x['id'],recipients=sorted(set(x['attendees']))) for x in selected])
@operation('seminar_ride', '''输入含events同meeting_cancel_plan、seminar_id、lead_minutes:int>=0。seminar_id必须对应kind="seminar"，返回{event_id,pickup:该start-lead_minutes,destination:输入destination非空str}；时间允许负数（固定纪元分钟）。不依赖取消列表，不误选最近普通会议。''')
def seminar_ride(p,c):
    d=raw(p); events={x['id']:x for x in unique(rows(d,'events'))}; e=events[string(d,'seminar_id')]; require(string(e,'kind')=='seminar')
    return dict(event_id=e['id'],pickup=ints(e,'start')-ints(d,'lead_minutes',0),destination=string(d,'destination'))
@operation('book_purchase', '''输入含books:[{id,title,language,price_cents:int>=0,rating:int>=0}],book_query:{keyword,language,max_price_cents:int>=0}。title按casefold子串，语言精确匹配，价格<=上限；选rating最高、价格最低、id最小。返回{book_id:str或null,price_cents:int或null}，空候选不购买。''')
def book_purchase(p,c):
    d=raw(p); q=obj(field(d,'book_query')); needle=string(q,'keyword').casefold(); language=string(q,'language'); cap=ints(q,'max_price_cents',0); choices=[]
    for b in unique(rows(d,'books')):
        ints(b,'price_cents',0); ints(b,'rating',0)
        if needle in string(b,'title').casefold() and string(b,'language')==language and b['price_cents']<=cap:choices.append(b)
    best=min(choices,key=lambda x:(-x['rating'],x['price_cents'],x['id'])) if choices else None
    return dict(book_id=best['id'] if best else None,price_cents=best['price_cents'] if best else None)
def f11(s):
    return dict(window=[0,1000],cancel_organizer='other',events=[dict(id=f'e{i}',start=100*i,end=100*i+50,kind='seminar' if i==5 else 'meeting',organizer='other' if i%2 else 'self',attendees=['a','b','a']) for i in range(10)],seminar_id='e5',lead_minutes=30,destination=f'campus{s}',books=[dict(id=f'b{s}-{i}',title='Graph handbook',language='en' if i%2 else 'zh',price_cents=1000+i*100,rating=i%4) for i in range(12)],book_query=dict(keyword='graph',language='en',max_price_cents=1900))
task('MP11','meeting_ride_book_plan','reasoning4',[('engines/cancellations',component('cancellations','meeting_cancel_plan')),('engines/ride',component('ride','seminar_ride')),('engines/books',component('books','book_purchase'))],f11)

@operation('download_archive', '''输入含files:[{path,hex}],download_prefix:str,archive_prefix:str,extensions:{扩展名含点:子目录名}。只处理download_prefix直接子文件，扩展名大小写不敏感，按extensions选择归档子目录，目标archive_prefix/子目录/原basename。未匹配/深层文件保留；目标已存在报错。返回{moves:[{from,to}]}按from，安全路径规则同公共规范。''')
def download_archive(p,c):
    d=raw(p); fs=files(d); src=safe_path(string(d,'download_prefix'))+'/'; dst=safe_path(string(d,'archive_prefix')); extensions=obj(field(d,'extensions')); out=[]
    for ext,folder in extensions.items():require(ext.startswith('.')); safe_path(folder)
    for path in sorted(fs):
        if not path.startswith(src) or '/' in path[len(src):]:continue
        suffix=PurePosixPath(path).suffix.lower()
        if suffix in extensions:
            target=dst+'/'+extensions[suffix]+'/'+PurePosixPath(path).name; require(target not in fs); out.append({'from':path,'to':target})
    require(len({x['to'] for x in out})==len(out)); return dict(moves=out)
@operation('mail_trash', '''输入含emails:[{id,date:YYYY-MM-DD,subject:str,folder:str,sender:str,thread_id:str}],month:YYYY-MM,trash_keyword:str。选择日期属于month且subject按casefold子串命中且folder!="TRASH"，返回{trash_ids:排序ID}；日期必须合法，不匹配邮件保持原状。''')
def mail_trash(p,c):
    d=raw(p); month=string(d,'month'); require(re.fullmatch(r'\d{4}-\d{2}',month) is not None); datetime.date.fromisoformat(month+'-01'); kw=string(d,'trash_keyword').casefold(); ids=[]
    for m in unique(rows(d,'emails')):
        date=datetime.date.fromisoformat(string(m,'date')).isoformat()
        if date.startswith(month+'-') and kw in string(m,'subject',True).casefold() and string(m,'folder')!='TRASH':ids.append(m['id'])
    return dict(trash_ids=sorted(ids))
@operation('manager_reply', '''输入含emails同mail_trash、reply_email_id、manager、reply_text。目标必须存在且sender==manager；直接按目标ID回复，不按主题挑最新邮件。返回{email_id,thread_id,to:manager,text:reply_text}，reply_text可为空串。''')
def manager_reply(p,c):
    d=raw(p); messages={x['id']:x for x in unique(rows(d,'emails'))}; m=messages[string(d,'reply_email_id')]; require(string(m,'sender')==string(d,'manager'))
    return dict(email_id=m['id'],thread_id=string(m,'thread_id'),to=d['manager'],text=string(d,'reply_text',True))
@operation('workspace_commit', '''输入依次原快照、download_archive、mail_trash、manager_reply。若目标回复邮件也在本批trash_ids，报ValueError（提交前冲突）。按moves重放文件迁移，按trash_ids将对应邮件folder设TRASH，输出{files:[{path,hex}]按path,emails:按id,reply:上游回复}；禁止触碰其他文件/邮件。''')
def workspace_commit(p,c):
    d=raw(p); fs=files(d); trash=rows(raw(p,2),'trash_ids'); reply=raw(p,3); require(reply['email_id'] not in trash)
    for r in rows(raw(p,1),'moves'): require(r['from'] in fs and r['to'] not in fs); fs[r['to']]=fs.pop(r['from'])
    emails=unique(rows(d,'emails')); require(set(trash)<={x['id'] for x in emails})
    return dict(files=[dict(path=k,hex=v) for k,v in sorted(fs.items())],emails=sorted([{**x,'folder':'TRASH'} if x['id'] in trash else x for x in emails],key=lambda x:x['id']),reply=reply)
def f12(s):
    return dict(files=[dict(path=x,hex=(x+str(s)).encode().hex()) for x in ['Downloads/a.PDF','Downloads/b.jpg','Downloads/nested/c.pdf','Downloads/keep.exe']],download_prefix='Downloads',archive_prefix='Archive',extensions={'.pdf':'docs','.jpg':'photos'},emails=[dict(id=f'm{i}',date='2026-11-03' if i%2 else '2026-10-30',subject='newsletter' if i<6 else 'Update',folder='INBOX',sender='manager' if i==7 else 'friend',thread_id=f't{i}') for i in range(8)],month='2026-11',trash_keyword='news',reply_email_id='m7',manager='manager',reply_text=f'Confirmed {s}')
task('MP12','files_mail_workspace','linux2',[('products/files',component('files','download_archive')),('products/mail',component('mail','mail_trash')),('products/reply',component('reply','manager_reply')),('products/commit',component('commit','workspace_commit',['inputs/case.json',output('files'),output('mail'),output('reply')]))],f12)

def grouped(d):
    gs={}
    for r in unique(rows(d,'records')):gs.setdefault(string(r,'key'),[]).append(r)
    return gs
@operation('numeric_features', '''输入{records:[{id,key,value:有限数或null,category:str或null,time:int或null}],vocabulary:[唯一非空str]}。按key分组，忽略value=null，返回{rows:[{key,values:{count,sum,mean}}]}，按key排序；全null组count=0,sum=0,mean=null。sum不按记录ID去重，记录ID必须唯一。''')
def numeric_features(p,c):
    out=[]
    for k,rs in sorted(grouped(raw(p)).items()):
        vs=[number(field(r,'value')) for r in rs if field(r,'value') is not None]; out.append(dict(key=k,values=dict(count=len(vs),sum=sum(vs),mean=sum(vs)/len(vs) if vs else None)))
    return dict(rows=out)
@operation('category_features', '''输入同numeric_features。vocabulary固定顺序且无重复。对每组非null category检查字符串；输出每个词是否出现的布尔列，列名直接为词表项。全null组不输出该key，未知类别不增加列。返回{rows:[{key,values:{词表项:bool}}]}按key排序。''')
def category_features(p,c):
    d=raw(p); vocab=rows(d,'vocabulary'); require(len(set(vocab))==len(vocab)); [text(x) for x in vocab]; out=[]
    for k,rs in sorted(grouped(d).items()):
        values=[text(field(r,'category')) for r in rs if field(r,'category') is not None]
        if values:out.append(dict(key=k,values={v:x in values for v in vocab for x in [v]}))
    return dict(rows=out)
@operation('time_features', '''输入同numeric_features。按key收集非null整数time，输出{rows:[{key,values:{first,last,span:last-first}}]}按key排序；全null时间组省略。time可以为负，不能按输入行首尾代替min/max。''')
def time_features(p,c):
    out=[]
    for k,rs in sorted(grouped(raw(p)).items()):
        vs=[integer(field(r,'time')) for r in rs if field(r,'time') is not None]
        if vs:out.append(dict(key=k,values=dict(first=min(vs),last=max(vs),span=max(vs)-min(vs))))
    return dict(rows=out)
@operation('feature_union', '''输入依次为numeric_features、category_features、time_features。对各自产出key做外连接，按key排序。列名分别加num./cat./time.前缀；columns为所有列名的字典序并集。每行values按所有columns补齐，缺支路填null（不能填0）。返回{index:[key],columns:[列名],data:[[值]]}。只使用特征输出key，不能强行换回原输入索引。''')
def feature_union(p,c):
    by={}; columns=set()
    for prefix,d in zip(['num','cat','time'],[raw(p,i) for i in range(3)]):
        for r in unique(rows(d,'rows'),'key'):
            values={prefix+'.'+k:v for k,v in obj(field(r,'values')).items()}; columns.update(values); by.setdefault(r['key'],{}).update(values)
    columns=sorted(columns); keys=sorted(by); return dict(index=keys,columns=columns,data=[[by[k].get(col) for col in columns] for k in keys])
def f13(s):
    return dict(records=[dict(id=f'r{s}-{i}',key=f'g{i%4}',value=None if i%3==0 else i+s,category=None if i%4==0 else ['red','blue','other'][i%3],time=None if i%4==0 else (15-i)*3) for i in range(16)],vocabulary=['red','blue'])
task('MP13','grouped_feature_union','reasoning4',[('engines/numeric',component('numeric','numeric_features')),('engines/category',component('category','category_features')),('engines/time',component('time','time_features')),('engines/union',component('union','feature_union',[output('numeric'),output('category'),output('time')]))],f13)

def exception_nodes(d):
    nodes={r['id']:r for r in unique(rows(d,'nodes'))}; root=string(d,'root'); require(root in nodes)
    for r in nodes.values():
        string(r,'type'); string(r,'message',True); boolean(field(r,'suppress_context')); rows(r,'frames')
        for k in ('cause','context'):
            x=field(r,k); require(x is None or x in nodes)
    return nodes,root
@operation('exception_chain', '''输入{root:异常ID,nodes:[{id,type,message,cause:ID或null,context:ID或null,suppress_context:bool,frames:[{file,line:int>=1,function,locals:object}]}]}。cause非null时优先追cause，否则仅suppress_context=false时追context。对root可达的有效链做环检测、长度上限8，违规ValueError；不追被抑制的context，非链节点仍校验基本字段。返回{chain:[{id,type,message,link:cause/context/null}]}从最内层到root；每项link为该节点到前一项的关联，首项null。''')
def exception_chain(p,c):
    nodes,root=exception_nodes(raw(p)); seen=set(); stack=[]; id_=root
    while id_ is not None:
        require(id_ not in seen and len(stack)<8,'exception chain cycle/depth'); seen.add(id_); r=nodes[id_]; link='cause' if r['cause'] is not None else ('context' if r['context'] is not None and not r['suppress_context'] else None); stack.append(dict(id=id_,type=r['type'],message=r['message'],link=link)); id_=r[link] if link else None
    return dict(chain=list(reversed(stack)))
@operation('portable_frames', '''输入同exception_chain。处理全部nodes的frames，文件路径先把反斜线改/再只保留basename，line严格正整数，function非空。locals的JSON值用ensure_ascii=False/键排序/紧凑分隔符序列化成字符串，不执行repr或源码。返回{frames:{异常ID:[{file,line,function,locals:{变量名:规范JSON字符串}}]}}；保留每个异常的frame输入顺序。''')
def portable_frames(p,c):
    nodes,_=exception_nodes(raw(p)); out={}
    for id_,r in nodes.items():
        result=[]
        for f in rows(r,'frames'):
            name=PurePosixPath(string(f,'file').replace('\\','/')).name; require(name); result.append(dict(file=name,line=ints(f,'line',1),function=string(f,'function'),locals={k:canonical(v) for k,v in obj(field(f,'locals')).items()}))
        out[id_]=result
    return dict(frames=out)
@operation('exception_report', '''输入依次为exception_chain、portable_frames。按chain顺序输出lines：非首项先加"--- direct cause ---"（link=cause）或"--- during handling ---"（context）；随后每frame一行"  file:line in function"，再一行"Type: message"。locals不嵌入展示，但须保留在report.nodes各节点frames中。返回{nodes:[{id,type,message,link,frames}],text:以换行连接lines并在非空时结尾加换行}。''')
def exception_report(p,c):
    chain=rows(raw(p),'chain'); frames=obj(field(raw(p,1),'frames')); out=[]; lines=[]
    for i,r in enumerate(chain):
        if i:lines.append('--- direct cause ---' if r['link']=='cause' else '--- during handling ---')
        fs=seq(frames[r['id']]); out.append({**r,'frames':fs})
        lines.extend(f"  {f['file']}:{f['line']} in {f['function']}" for f in fs); lines.append(r['type']+': '+r['message'])
    return dict(nodes=out,text='\n'.join(lines)+('\n' if lines else ''))
def f14(s):
    return dict(root='outer',nodes=[dict(id='inner',type='KeyError',message=f'key{s}',cause=None,context=None,suppress_context=False,frames=[dict(file='C:\\user\\module.py',line=3,function='lookup',locals=dict(key='x'))]),dict(id='hidden',type='ValueError',message='ignored',cause=None,context=None,suppress_context=False,frames=[]),dict(id='outer',type='RuntimeError',message='failed',cause='inner' if s%2 else None,context='hidden',suppress_context=s%3==0,frames=[dict(file='/tmp/app.py',line=8,function='run',locals=dict(data=[1,True,None]))])])
task('MP14','portable_exception_report','context8',[('chain',component('chain','exception_chain')),('frames',component('frames','portable_frames')),('report',component('report','exception_report',[output('chain'),output('frames')]))],f14)
