from common import *
import csv, io, datetime

@operation('fit_members', '''输入 {classes:[唯一非空字符串],sample_weight:[非负数],members:[{id,active:bool,weight:非负数,predictions:[类别],classes:[类别],probabilities:[[概率]]}]}。sample_weight 长度为样本数。成员ID唯一；关闭成员仅校验id/active，不读取其余字段。返回 {classes,sample_count,members:[原活动成员的深拷贝并增加fit_weight:原sample_weight]}，保留输入成员顺序。活动成员至少一个且权重和>0；其predictions长度须等于样本数、标签属于全局类别，classes必须为全局类别的一个排列；概率矩阵尺寸一致、各项>=0且每行和距1不超过1e-9。不执行真实训练。''')
def fit_members(p,c):
    d=raw(p); classes=seq(field(d,'classes')); require(classes and len(set(classes))==len(classes)); [text(x) for x in classes]
    sw=seq(field(d,'sample_weight')); [require(number(x)>=0) for x in sw]
    members=[]
    for m in unique(rows(d,'members')):
        if not boolean(field(m,'active')): continue
        require(number(field(m,'weight'))>=0)
        pred=rows(m,'predictions'); require(len(pred)==len(sw) and all(x in classes for x in pred))
        order=rows(m,'classes'); require(len(order)==len(classes) and set(order)==set(classes))
        probs=rows(m,'probabilities'); require(len(probs)==len(sw))
        for row in probs:
            seq(row); require(len(row)==len(order)); [require(number(v)>=0) for v in row]; require(abs(sum(row)-1)<=1e-9)
        members.append({**m,'fit_weight':sw[:]})
    require(members and sum(m['weight'] for m in members)>0)
    return dict(classes=classes,sample_count=len(sw),members=members)

@operation('hard_vote', '''唯一输入为fit_members的结果封装。逐样本按成员weight累加predictions的类别票数；平局按全局classes的先后次序。返回 {predictions:[类别],scores:[[按全局classes排列的未归一票数]]}。必须使用上游已筛选成员和权重，不读取固定训练样例。''')
def hard_vote(p,c):
    d=raw(p); cs=rows(d,'classes'); ms=rows(d,'members'); n=ints(d,'sample_count',0); scores=[]
    for i in range(n): scores.append([sum(m['weight'] for m in ms if m['predictions'][i]==k) for k in cs])
    return dict(predictions=[cs[max(range(len(cs)),key=lambda j:r[j])] for r in scores],scores=scores)

@operation('soft_vote', '''唯一输入为fit_members结果。将各成员probabilities的列按该成员classes映射到全局classes，然后按weight加权平均。返回 {predictions,probabilities}，预测平局按全局classes顺序；不能假定各成员的概率列顺序相同。''')
def soft_vote(p,c):
    d=raw(p); cs=rows(d,'classes'); ms=rows(d,'members'); n=ints(d,'sample_count',0); total=sum(m['weight'] for m in ms)
    probs=[[sum(m['weight']*m['probabilities'][i][m['classes'].index(k)] for m in ms)/total for k in cs] for i in range(n)]
    return dict(predictions=[cs[max(range(len(cs)),key=lambda j:r[j])] for r in probs],probabilities=probs)

@operation('vote_comparison', '''输入依次为硬投票、软投票结果。样本数不一致报ValueError；返回 {hard:硬预测,soft:软预测,disagreements:[两路预测不同的样本下标]}。''')
def vote_comparison(p,c):
    a=rows(raw(p),'predictions'); b=rows(raw(p,1),'predictions'); require(len(a)==len(b))
    return dict(hard=a,soft=b,disagreements=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y])

def f01(s):
    return dict(classes=['red','blue'],sample_weight=[1,2,0,1],members=[dict(id=f'm{s}-{i}',active=i!=1,weight=i+1,predictions=['blue','red','red','blue'],classes=['blue','red'] if i%2 else ['red','blue'],probabilities=([[.8,.2],[.3,.7],[.6,.4],[.2,.8]] if i%2 else [[.2,.8],[.7,.3],[.4,.6],[.8,.2]])) for i in range(4)])
task('MP01','weighted_voting','multistage4',[('domains/fit',component('fit','fit_members')),('views/hard',component('hard','hard_vote',[output('fit')])),('views/soft',component('soft','soft_vote',[output('fit')])),('views/comparison',component('comparison','vote_comparison',[output('hard'),output('soft')]))],f01)

def piece_info(d):
    y=rows(d,'columns'); require(len(set(y))==len(y)); [text(x) for x in y]
    ps=unique(rows(d,'pieces')); seen=set()
    for x in ps:
        co=rows(x,'coordinates'); da=rows(x,'data'); require(len(co)==len(da)); obj(field(x,'attrs'))
        for k,row in zip(co,da):
            number(k); require(k not in seen,'overlapping coordinate'); seen.add(k); seq(row); require(len(row)==len(y)); [number(v) for v in row]
    return y,ps

@operation('segment_index', '''输入 {columns:[唯一列名],pieces:[{id,coordinates:[唯一有限数],data:[[有限数]],attrs:object}],attribute_policy:drop_conflicts/first}。只有coordinates轴变化，columns保持给定顺序；data每行宽度等于columns长度。piece ID唯一，所有坐标跨片唯一，不允许重叠。返回 {columns,order:[{coordinate,piece,row}]}，order按coordinate升序；piece为源ID，row为源行下标。空片及空输入合法。''')
def segment_index(p,c):
    y,ps=piece_info(raw(p)); return dict(columns=y,order=sorted([dict(coordinate=k,piece=x['id'],row=i) for x in ps for i,k in enumerate(x['coordinates'])],key=lambda r:r['coordinate']))

@operation('segment_attributes', '''输入同segment_index。仅合并pieces.attrs：first对每键选择原pieces顺序中第一个出现值；drop_conflicts仅保留所有已出现值相同的键，缺失不算冲突。值以JSON深度相等比较，返回 {attrs:合并字典,conflicts:有不同值的键排序列表}。不按坐标排序改变属性优先级。''')
def segment_attributes(p,c):
    d=raw(p); _,ps=piece_info(d); mode=string(d,'attribute_policy'); require(mode in ('first','drop_conflicts')); attrs={}; conflict=[]
    for k in sorted(set().union(*(set(x['attrs']) for x in ps))):
        vs=[x['attrs'][k] for x in ps if k in x['attrs']]; diff=any(v!=vs[0] for v in vs)
        if diff: conflict.append(k)
        if mode=='first' or not diff: attrs[k]=vs[0]
    return dict(attrs=attrs,conflicts=conflict)

@operation('segment_assemble', '''输入依次为原输入、segment_index、segment_attributes。按上游order定位原piece/row，输出 {coordinates,columns,data,attrs,attribute_conflicts}。输出列保持原columns顺序；禁止对旁观轴排序。必须实际使用两路上游结果。''')
def segment_assemble(p,c):
    d=raw(p); ix=raw(p,1); at=raw(p,2); ps={x['id']:x for x in rows(d,'pieces')}
    return dict(coordinates=[x['coordinate'] for x in rows(ix,'order')],columns=rows(ix,'columns'),data=[ps[x['piece']]['data'][x['row']] for x in ix['order']],attrs=obj(field(at,'attrs')),attribute_conflicts=rows(at,'conflicts'))
def f02(s):
    return dict(columns=['a','c','b'],attribute_policy='drop_conflicts' if s%2 else 'first',pieces=[dict(id=f'p{s}-{i}',coordinates=[i+4,i],data=[[i,20+s,30],[i+10,s,0]],attrs=dict(unit='m',site=str(i%2))) for i in range(4)])
task('MP02','single_axis_concat','multistage4',[('domains/index',component('index','segment_index')),('domains/attributes',component('attributes','segment_attributes')),('views/table',component('table','segment_assemble',['inputs/case.json',output('index'),output('attributes')]))],f02)

def mount_record(device,mount,fs,options):
    def unesc(x): return x.replace('\\040',' ').replace('\\011','\t').replace('\\134','\\')
    return dict(device=unesc(text(device)),mount=unesc(text(mount)),fstype=text(fs),options=sorted(set(text(options).split(','))))
@operation('fstab_parse', '''输入含fstab:str。逐行去首尾空白，忽略空行和#开头注释；其他行按空白切成4到6列，前4列为device,mount,fstype,options。字段中的\\040、\\011、\\134分别解为空格、tab、反斜线。返回 {records:[{device,mount,fstype,options:逗号分割去重排序}]}，保持行序；不读取真实系统。''')
def fstab_parse(p,c):
    rs=[]
    for line in string(raw(p),'fstab',True).splitlines():
        line=line.strip()
        if not line or line.startswith('#'):continue
        x=line.split(); require(4<=len(x)<=6); rs.append(mount_record(*x[:4]))
    return dict(records=rs)
@operation('aix_parse', '''输入含aix:str。忽略空行/#注释；以非缩进的“挂载点:”开始段落，段内key=value可含空白。只支持dev、vfs、options，未知或重复key报错。dev必需，vfs缺省jfs2，options缺省rw；段头为mount。输出同fstab_parse，保持段序；无段头属性/缺设备报ValueError。''')
def aix_parse(p,c):
    result=[]; current=None
    for ln in string(raw(p),'aix',True).splitlines():
        if not ln.strip() or ln.strip().startswith('#'):continue
        if not ln[0].isspace() and ln.rstrip().endswith(':'):
            if current: result.append(current)
            current={'mount':ln.strip()[:-1]}
        else:
            require(current is not None and '=' in ln); k,v=ln.strip().split('=',1); k=k.strip(); require(k in ('dev','vfs','options') and k not in current); current[k]=v.strip()
    if current: result.append(current)
    return dict(records=[mount_record(string(r,'dev'),r['mount'],r.get('vfs','jfs2'),r.get('options','rw')) for r in result])
@operation('mount_parse', '''输入含mount:str。固定Linux语法“device on mountpoint type fstype (option1,option2)”；一条记录一行，空行忽略。device/mountpoint可含\\040但不含裸空白，fstype无空白，括号内不能为空。输出同fstab_parse；不支持其他OS的自由格式。''')
def mount_parse(p,c):
    result=[]
    for ln in string(raw(p),'mount',True).splitlines():
        if not ln.strip():continue
        m=re.fullmatch(r'(\S+) on (\S+) type (\S+) \(([^()]+)\)',ln.strip()); require(m is not None); result.append(mount_record(*m.groups()))
    return dict(records=result)
@operation('mount_merge', '''输入依次为fstab、aix、mount解析结果。按此固定来源优先级、再原记录行序为每个mount选首条；返回 {records:按mount排序并增加source的胜出记录,conflicts:[{mount,evidence:[增加source的全部记录]}]}。同点只要device/fstype/options任一不同即冲突，证据包含相同的重复记录；完全相同则不报冲突。''')
def mount_merge(p,c):
    by={}
    for source,d in zip(['fstab','aix','mount'],map(lambda i:raw(p,i),range(3))):
        for r in rows(d,'records'): by.setdefault(r['mount'],[]).append({**r,'source':source})
    return dict(records=[v[0] for k,v in sorted(by.items())],conflicts=[dict(mount=k,evidence=v) for k,v in sorted(by.items()) if len({canonical({a:b for a,b in r.items() if a!='source'}) for r in v})>1])
def f03(s):
    return dict(fstab=f'# fixture\n/dev/d{s} /data ext4 rw,nosuid 0 2\n/dev/x /with\\040space xfs ro\n',aix='/data:\n  dev = /dev/aix\n  options = rw\n/backup:\n  dev = /dev/b\n',mount=f'/dev/live on /data type ext4 (rw,relatime)\ntmpfs on /tmp{s} type tmpfs (rw)\n')
task('MP03','offline_mount_facts','multistage4',[('domains/fstab',component('fstab','fstab_parse')),('domains/aix',component('aix','aix_parse')),('domains/mount',component('mount','mount_parse')),('views/merged',component('merged','mount_merge',[output('fstab'),output('aix'),output('mount')]))],f03)

def normalize_user(r):
    obj(r); id_=r.get('user_id',r.get('id')); require(type(id_) in (str,int) and str(id_).strip()); out={'id':str(id_).strip()}
    for dest,alias in [('name','full_name'),('email','mail'),('joined','joined_at')]:
        v=r[dest] if dest in r else r.get(alias)
        if v is None:continue
        text(v,True)
        if dest=='joined' and v:
            try: v=datetime.datetime.strptime(v,'%Y-%m-%d' if '-' in v else '%d/%m/%Y').date().isoformat()
            except ValueError: raise ValueError('invalid date')
        out[dest]=v
    return out
def normalized_users(rs):
    by={}
    for r in rs:
        v=normalize_user(r); by.setdefault(v['id'],{'id':v['id']}).update(v)
    return dict(records=[v for k,v in sorted(by.items())])
@operation('users_json', '''输入含json_text:str，其内容为对象数组。每行规范为{id:str,name?,email?,joined?}。user_id优先id；ID为非空str或int（bool非法），str.strip后返回。name/full_name、email/mail、joined/joined_at使用新字段存在优先；null/缺失不赋值，空串是有效值。joined非空时只接受YYYY-MM-DD或DD/MM/YYYY并转ISO日期。同源重复ID按原顺序逐字段最后一个存在值胜出。输出{records:按ID字典序}；未知字段忽略。''')
def users_json(p,c): return normalized_users(seq(json.loads(string(raw(p),'json_text',True))))
@operation('users_csv', '''输入含csv_text:str，CSV首行为表头，支持标准双引号转义/逗号/嵌入换行，必须有id或user_id列；列名唯一且无缺列/额外列。规范与users_json相同，但CSV空单元格视为缺失值（不清空旧值）。空文本返回空records；重复源ID逐字段最后存在值胜出。''')
def users_csv(p,c):
    value=string(raw(p),'csv_text',True)
    if not value:return dict(records=[])
    reader=csv.DictReader(io.StringIO(value,newline='')); names=reader.fieldnames; require(names and len(names)==len(set(names)) and ('id' in names or 'user_id' in names))
    rs=[]
    for r in reader:
        require(None not in r and None not in r.values()); rs.append({k:v for k,v in r.items() if v!=''})
    return normalized_users(rs)
@operation('users_jsonl', '''输入含jsonl_text:str。忽略纯空白行，每个其余物理行必须是一个JSON对象；坏JSON立即ValueError。其余规范、同源重复和空串规则同users_json，输出{records:按ID排序}。''')
def users_jsonl(p,c): return normalized_users([obj(json.loads(x)) for x in string(raw(p),'jsonl_text',True).splitlines() if x.strip()])
@operation('users_merge', '''输入依次为JSON、CSV、JSONL规范记录；来源名固定json/csv/jsonl。逐字段选首个存在值，按该来源优先级，null已在解析层移除，空串参与优先级。输出 {users:[合并用户按id],conflicts:[{id,field,values:[{source,value}]}]}；不同来源中同字段出现两个以上不同值时列出全部来源证据，conflicts按(id,field)。包含仅出现在低优先级来源的用户。''')
def users_merge(p,c):
    by={}
    for source,d in zip(['json','csv','jsonl'],[raw(p,i) for i in range(3)]):
        for r in rows(d,'records'): by.setdefault(r['id'],[]).append((source,r))
    users=[]; conflicts=[]
    for id_,rs in sorted(by.items()):
        user={'id':id_}
        for k in ['email','joined','name']:
            vs=[dict(source=s,value=r[k]) for s,r in rs if k in r]
            if vs:user[k]=vs[0]['value']
            if len({canonical(v['value']) for v in vs})>1:conflicts.append(dict(id=id_,field=k,values=vs))
        users.append(user)
    return dict(users=users,conflicts=conflicts)
def f04(s):
    a=[dict(id=i+s*100,name=f'User {i}',email=f'{i}@a',joined='2024-01-03') for i in range(8)]
    b='user_id,full_name,mail,joined_at\n'+''.join(f'{i+s*100},"Doe, {i}",{i}@b,03/01/2024\n' for i in range(4,12))
    return dict(json_text=json.dumps(a),csv_text=b,jsonl_text='\n'.join(json.dumps(dict(id=i+s*100,email='',name=f'New\n{i}')) for i in range(10,15)))
task('MP04','multiformat_user_merge','multistage4',[('domains/json_users',component('json_users','users_json')),('domains/csv_users',component('csv_users','users_csv')),('domains/jsonl_users',component('jsonl_users','users_jsonl')),('views/directory',component('directory','users_merge',[output('json_users'),output('csv_users'),output('jsonl_users')]))],f04)

def contacts(d): return {r['id']:r for r in unique(rows(d,'contacts'))}
@operation('group_candidates', '''输入含contacts:[{id,age:int>=0}]、self_id、keyword非空str、groups:[{id,members:[contact_id],messages:[str]}]。任何消息casefold后包含keyword时，提取该群全部members，排除self_id，去重排序。所有成员必须存在；返回{ids}，不是只提取发言人。''')
def group_candidates(p,c):
    d=raw(p); ct=contacts(d); keyword=string(d,'keyword').casefold(); result=set()
    for g in unique(rows(d,'groups')):
        members=rows(g,'members'); require(all(x in ct for x in members)); messages=rows(g,'messages'); [text(x,True) for x in messages]
        if any(keyword in x.casefold() for x in messages):result.update(members)
    return dict(ids=sorted(result-{string(d,'self_id')}))
@operation('mail_candidates', '''输入含contacts、self_id、keyword、emails:[{id,sender:contact_id,subject:str}]。subject不区分大小写包含keyword的发件人构成候选，排除自己，去重排序。未知sender报错；返回{ids}。''')
def mail_candidates(p,c):
    d=raw(p); ct=contacts(d); result=set(); kw=string(d,'keyword').casefold()
    for m in unique(rows(d,'emails')):
        sender=string(m,'sender'); require(sender in ct)
        if kw in string(m,'subject',True).casefold():result.add(sender)
    return dict(ids=sorted(result-{string(d,'self_id')}))
@operation('shared_durations', '''输入含contacts、self_id、window:[start,end]和events:[{id,start:int,end:int,attendees:[id]}]，所有时间为同一固定时区的整数分钟，end>start。只计包含self_id的活动，按半开窗口裁剪时长；同一事件重复参会人只算一次，不合并两个重叠事件。返回{minutes:{每个非自己contact_id:累计分钟数}}，包括0时长联系人。''')
def shared_durations(p,c):
    d=raw(p); ct=contacts(d); me=string(d,'self_id'); require(me in ct); window=rows(d,'window'); require(len(window)==2); lo,hi=[integer(x) for x in window]; require(lo<hi); totals={x:0 for x in ct if x!=me}
    for e in unique(rows(d,'events')):
        start=ints(e,'start'); end=ints(e,'end'); require(end>start); ids=set(rows(e,'attendees')); require(ids<=ct.keys())
        if me in ids:
            for x in ids-{me}:totals[x]+=max(0,min(end,hi)-max(start,lo))
    return dict(minutes=totals)
@operation('contact_rank', '''输入依次为原快照、群候选、邮件候选、日历时长。候选取并集，不取交集；按累计分钟降序、age降序、contact_id升序排序。返回{ranking:[{id,minutes,age}],winner:第一名id或null}；所有age为非负整数。''')
def contact_rank(p,c):
    d=raw(p); ct=contacts(d); ids=set(rows(raw(p,1),'ids'))|set(rows(raw(p,2),'ids')); minutes=obj(field(raw(p,3),'minutes'))
    out=[dict(id=x,minutes=integer(minutes[x],0),age=ints(ct[x],'age',0)) for x in ids]; out.sort(key=lambda r:(-r['minutes'],-r['age'],r['id']))
    return dict(ranking=out,winner=out[0]['id'] if out else None)
def f05(s):
    ids=['self']+[f'c{s}-{i}' for i in range(8)]
    return dict(contacts=[dict(id=x,age=20+i) for i,x in enumerate(ids)],self_id='self',keyword='dinner',window=[0,500],groups=[dict(id='g',members=ids[:5],messages=['DINNER soon'])],emails=[dict(id=f'e{i}',sender=x,subject='Dinner plan') for i,x in enumerate(ids[3:])],events=[dict(id=f'v{i}',start=i*50-10,end=i*50+80,attendees=['self',x,x]) for i,x in enumerate(ids[1:])])
task('MP05','cross_app_contact_ranking','multistage4',[('domains/groups',component('groups','group_candidates')),('domains/mail',component('mail','mail_candidates')),('domains/calendar',component('calendar','shared_durations')),('views/ranking',component('ranking','contact_rank',['inputs/case.json',output('groups'),output('mail'),output('calendar')]))],f05)

@operation('cancel_morning', '''输入{events:[{id,start:int,end:int,social:bool,cancelled:bool,attendees:[contact_id]}],day:int>=0,contacts:[{id,email:str或null,message:str或null,chat:str或null}]}；时间为分钟。选择start在[day*1440,day*1440+720)且social且未cancelled的活动，end>start。返回{cancelled:目标id排序,snapshots:目标原记录按id,remaining:其余原记录按id}。不删除已经取消的旧记录。''')
def cancel_morning(p,c):
    d=raw(p); day=ints(d,'day',0); events=unique(rows(d,'events')); targets=[]
    for e in events:
        start=ints(e,'start'); require(ints(e,'end')>start); social=boolean(field(e,'social')); cancelled=boolean(field(e,'cancelled')); rows(e,'attendees')
        if day*1440<=start<day*1440+720 and social and not cancelled:targets.append(e)
    targets.sort(key=lambda x:x['id']); ids={x['id'] for x in targets}
    return dict(cancelled=sorted(ids),snapshots=targets,remaining=sorted([x for x in events if x['id'] not in ids],key=lambda x:x['id']))
@operation('channel_directory', '''输入同cancel_morning。联系人ID唯一，email/message/chat必须为null或非空str。每人首选message，其次chat；email独立可用。返回{contacts:{id:{email,primary:message/chat/null,address:所选地址或null}}}。不因目前没有目标活动而忽略联系人校验。''')
def channel_directory(p,c):
    out={}
    for x in contacts(raw(p)).values():
        for k in ('email','message','chat'):
            if field(x,k) is not None:text(x[k])
        primary='message' if x['message'] is not None else ('chat' if x['chat'] is not None else None)
        out[x['id']]=dict(email=x['email'],primary=primary,address=x[primary] if primary else None)
    return dict(contacts=out)
@operation('cancel_notifications', '''输入依次为cancel_morning结果、channel_directory结果。将目标快照参会人取并集、去重，未知ID报错。返回{outbox:[{channel,to,recipients,requires}],unreachable:[id],group:null或{ id:"cancelled-social",members,requires }}。requires为全部本批cancelled ID排序。每个可email者独立email；message首选者组成一个新群，group.members按id、outbox增加一条message_group（to为群ID，recipients为成员）；chat回退者各发一条chat。两渠道均无者进入unreachable。outbox按(channel,to)排序，非群recipients=[contact_id]。先取消再通知且群先创建由requires及group表达，不执行真实发送。''')
def cancel_notifications(p,c):
    canc=raw(p); directory=obj(field(raw(p,1),'contacts')); ids=sorted({x for e in rows(canc,'snapshots') for x in rows(e,'attendees')}); require(set(ids)<=directory.keys()); req=rows(canc,'cancelled'); out=[]; group=[]; missing=[]
    for x in ids:
        r=directory[x]
        if r['email'] is not None:out.append(dict(channel='email',to=r['email'],recipients=[x],requires=req))
        if r['primary']=='message':group.append(x)
        elif r['primary']=='chat':out.append(dict(channel='chat',to=r['address'],recipients=[x],requires=req))
        elif r['email'] is None:missing.append(x)
    if group:out.append(dict(channel='message_group',to='cancelled-social',recipients=group,requires=req))
    return dict(outbox=sorted(out,key=lambda r:(r['channel'],r['to'])),unreachable=missing,group=dict(id='cancelled-social',members=group,requires=req) if group else None)
def f06(s):
    return dict(day=s,contacts=[dict(id=f'c{i}',email=f'{i}@x' if i%2 else None,message=f'm{i}' if i%3==0 else None,chat=f'h{i}' if i%3==1 else None) for i in range(6)],events=[dict(id=f'e{s}-{i}',start=s*1440+i*120,end=s*1440+i*120+60,social=i%3!=0,cancelled=i==2,attendees=[f'c{i%6}',f'c{(i+1)%6}']) for i in range(10)])
task('MP06','calendar_cancel_notify','multistage4',[('domains/calendar',component('calendar','cancel_morning')),('domains/channels',component('channels','channel_directory')),('views/notifications',component('notifications','cancel_notifications',[output('calendar'),output('channels')]))],f06)

def files(d):
    out={}
    for x in unique(rows(d,'files'),'path'):
        path=safe_path(x['path']); hx=string(x,'hex',True)
        try: bytes.fromhex(hx)
        except ValueError: raise ValueError('bad hex')
        out[path]=hx
    return out
@operation('attachment_receipts', '''输入{files:[{path:安全相对POSIX路径,hex:原字节十六进制}],attachments:[路径],recipients:[唯一非空id],send_ok:{recipient_id:bool},cleanup_prefix:str,archive_prefix:str}。附件去重排序且必须存在；recipients不重复。返回{attachments:[{path,sha256:原始字节摘要}],receipts:[{recipient,ok}]}，收件人按id排序，ok读取send_ok对应布尔值；不能以“尝试发送”当成功。''')
def attachment_receipts(p,c):
    d=raw(p); fs=files(d); paths=sorted(set(rows(d,'attachments'))); require(set(paths)<=fs.keys()); ids=rows(d,'recipients'); require(len(ids)==len(set(ids))); [text(x) for x in ids]; ok=obj(field(d,'send_ok'))
    return dict(attachments=[dict(path=x,sha256=hashlib.sha256(bytes.fromhex(fs[x])).hexdigest()) for x in paths],receipts=[dict(recipient=x,ok=boolean(ok[x])) for x in sorted(ids)])
@operation('independent_cleanup', '''输入同attachment_receipts。cleanup_prefix为安全目录名，不含尾斜线。选择该目录下所有以.tmp结尾的普通文件，返回{delete:[排序路径]}。按路径段边界匹配，home/tmp不应匹配home/tmp-old；不操作附件或归档。''')
def independent_cleanup(p,c):
    d=raw(p); fs=files(d); prefix=safe_path(string(d,'cleanup_prefix'))+'/'
    return dict(delete=sorted(x for x in fs if x.startswith(prefix) and x.endswith('.tmp')))
@operation('archive_after_send', '''输入依次为原快照、attachment_receipts、independent_cleanup。archive_prefix为安全相对目录。仅所有receipts.ok都为true且至少一位收件人时，按附件原完整路径拼到archive_prefix/下移动；其他情况完全不移动附件。清理delete始终可执行。任何重复目标、目标已存在、清理与移动源重叠均ValueError。输出{moves:[{from,to}],deleted:[path],blocked:bool,files:[{path,hex}]}，moves按from、files按path，字节不变。这是本地状态重放，不发邮件、不改真实home。''')
def archive_after_send(p,c):
    d=raw(p); fs=files(d); receipt=raw(p,1); cleanup=rows(raw(p,2),'delete'); prefix=safe_path(string(d,'archive_prefix')); passed=bool(rows(receipt,'receipts')) and all(boolean(r['ok']) for r in receipt['receipts']); moves=[]
    if passed:
        for a in rows(receipt,'attachments'):
            src=safe_path(a['path']); dst=prefix+'/'+src; require(src in fs and dst not in fs and src not in cleanup); moves.append({'from':src,'to':dst}); fs[dst]=fs.pop(src)
    for path in cleanup: require(path in fs); fs.pop(path)
    return dict(moves=sorted(moves,key=lambda r:r['from']),deleted=cleanup,blocked=not passed,files=[dict(path=k,hex=v) for k,v in sorted(fs.items())])
def f07(s):
    return dict(files=[dict(path=x,hex=(x+str(s)).encode().hex()) for x in ['downloads/report.txt','downloads/data.csv','home/tmp/a.tmp','home/tmp-old/b.tmp','home/keep.txt']],attachments=['downloads/report.txt','downloads/data.csv'],recipients=['ann','bob'],send_ok=dict(ann=True,bob=s%3!=1),cleanup_prefix='home/tmp',archive_prefix='archive')
task('MP07','send_archive_cleanup','linux2',[('products/receipts',component('receipts','attachment_receipts')),('products/cleanup',component('cleanup','independent_cleanup')),('products/archive',component('archive','archive_after_send',['inputs/case.json',output('receipts'),output('cleanup')]))],f07)
