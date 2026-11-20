from common import *
import ast, base64, fnmatch, io, zipfile

def source_tree(d):
    try: tree=ast.parse(string(d,'source',True),type_comments=True)
    except SyntaxError as e:raise ValueError('invalid Python') from e
    require(not any(isinstance(n,(ast.ClassDef,ast.Lambda,ast.AsyncFunctionDef)) for n in ast.walk(tree)),'unsupported Python scope')
    functions=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)]; require(all(n in tree.body for n in functions) and len({n.name for n in functions})==len(functions),'only unique module-level functions')
    for n in tree.body:
        if isinstance(n,ast.FunctionDef):require(not any(isinstance(x,ast.FunctionDef) for y in n.body for x in ast.walk(y)),'nested function unsupported')
    return tree
def scoped_nodes(tree):
    def visit(n,scope):
        yield n,scope
        if isinstance(n,ast.FunctionDef):
            for x in n.decorator_list:yield from visit(x,scope)
            for x in n.args.defaults+n.args.kw_defaults:
                if x is not None:yield from visit(x,scope)
            for x in n.body:yield from visit(x,n.name)
            return
        for x in ast.iter_child_nodes(n):yield from visit(x,scope)
    return list(visit(tree,'module'))
def ref_names(node,scope,line=None):
    return [dict(scope=scope,name=n.id,line=line if line is not None else n.lineno) for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)]
@operation('ordinary_uses', '''输入{source:Python源码}，只支持模块和模块直属普通函数且函数名不重复；类、lambda、async函数、嵌套/条件定义函数不在范围，遇到报ValueError。返回{uses:[{scope:"module"或函数名,name,line}]}，提取普通表达式Load名字，排除所有注解、类型注释和字符串内容；装饰器/默认值在module作用域，函数体在函数作用域。uses按(scope,line,name)排序并按三元组去重；不执行代码。''')
def ordinary_uses(p,c):
    tree=source_tree(raw(p)); out=[]
    def visit(n,scope):
        if isinstance(n,ast.FunctionDef):
            for x in n.decorator_list+n.args.defaults+[x for x in n.args.kw_defaults if x is not None]:visit(x,scope)
            for x in n.body:visit(x,n.name)
            return
        if isinstance(n,ast.AnnAssign):
            visit(n.target,scope)
            if n.value:visit(n.value,scope)
            return
        if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load):out.append((scope,n.lineno,n.id))
        for x in ast.iter_child_nodes(n):visit(x,scope)
    visit(tree,'module'); return dict(uses=[dict(scope=s,line=l,name=n) for s,l,n in sorted(set(out))])
@operation('annotation_uses', '''输入同ordinary_uses。提取AnnAssign.annotation及函数参数/返回注解中的Load名字；最外层字符串前向注解作为Python表达式再解析，坏表达式ValueError；不递归解释类型表达式内部字符串。函数签名注解归属module作用域，函数体赋值注解属于该函数；注解中的名字用注解所在源行号。返回与ordinary_uses相同uses结构和排序；不将普通字符串/docstring当注解。''')
def annotation_uses(p,c):
    tree=source_tree(raw(p)); out=[]
    for n,scope in scoped_nodes(tree):
        targets=[]
        if isinstance(n,ast.AnnAssign):targets=[n.annotation]
        elif isinstance(n,ast.FunctionDef):
            scope='module'; args=n.args.posonlyargs+n.args.args+n.args.kwonlyargs+[x for x in [n.args.vararg,n.args.kwarg] if x]; targets=[x.annotation for x in args if x.annotation]+([n.returns] if n.returns else [])
        for x in targets:
            node=x
            if isinstance(x,ast.Constant) and type(x.value) is str:
                try:node=ast.parse(x.value,mode='eval')
                except SyntaxError as e:raise ValueError('bad annotation') from e
            out.extend(ref_names(node,scope,x.lineno))
    return dict(uses=[dict(scope=s,line=l,name=n) for s,l,n in sorted({(r['scope'],r['line'],r['name']) for r in out})])
@operation('type_comment_uses', '''输入同ordinary_uses。仅支持赋值Assign上的# type:表达式。按表达式提取Load名字，line为该赋值语句行；函数签名type_comment或for/with类型注释报ValueError。# type:ignore不产生引用。返回同格式uses；不把文件任意注释里的单词算引用。''')
def type_comment_uses(p,c):
    out=[]
    for n,scope in scoped_nodes(source_tree(raw(p))):
        value=getattr(n,'type_comment',None)
        if not value:continue
        require(isinstance(n,ast.Assign),'only assignment type comments')
        try:expr=ast.parse(value,mode='eval')
        except SyntaxError as e:raise ValueError('bad type comment') from e
        out.extend(ref_names(expr,scope,n.lineno))
    return dict(uses=[dict(scope=s,line=l,name=n) for s,l,n in sorted({(r['scope'],r['line'],r['name']) for r in out})])
@operation('import_usage_join', '''输入依次原source、ordinary_uses、annotation_uses、type_comment_uses。仅支持绝对import/from且禁止*。import a.b绑定a，别名绑定别名；from a import B绑定B或别名。每(scope,绑定名)只能导入一次。函数内import优先；无本地import时，任何参数/赋值Store同名均遮蔽module导入，否则回退module；不分析global/nonlocal（出现报错）。模块引用仅匹配模块import。输出{imports:[{scope,name,module,line,used_by:[ordinary/annotation/comment按此序]}],unused:["scope:name"排序]}；imports按(scope,line,name)。字符串/docstring不构成使用。''')
def import_usage_join(p,c):
    tree=source_tree(raw(p)); bindings={}; locals_={}
    for n,scope in scoped_nodes(tree):
        require(not isinstance(n,(ast.Global,ast.Nonlocal)),'global unsupported')
        if isinstance(n,ast.FunctionDef):
            args=n.args.posonlyargs+n.args.args+n.args.kwonlyargs+[x for x in [n.args.vararg,n.args.kwarg] if x]; locals_.setdefault(n.name,set()).update(x.arg for x in args)
        if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store):locals_.setdefault(scope,set()).add(n.id)
        if isinstance(n,(ast.Import,ast.ImportFrom)):
            if isinstance(n,ast.ImportFrom):require(n.level==0 and n.module is not None)
            for a in n.names:
                require(a.name!='*'); name=a.asname or (a.name.split('.')[0] if isinstance(n,ast.Import) else a.name); key=(scope,name); require(key not in bindings,'duplicate import binding')
                module=a.name if isinstance(n,ast.Import) else n.module+'.'+a.name
                bindings[key]=dict(scope=scope,name=name,module=module,line=n.lineno,used_by=[])
    for label,i in [('ordinary',1),('annotation',2),('comment',3)]:
        for r in rows(raw(p,i),'uses'):
            scope=r['scope']; name=r['name']; key=(scope,name)
            if key not in bindings and scope!='module' and name not in locals_.get(scope,set()):key=('module',name)
            if key in bindings and label not in bindings[key]['used_by']:bindings[key]['used_by'].append(label)
    imports=sorted(bindings.values(),key=lambda r:(r['scope'],r['line'],r['name'])); return dict(imports=imports,unused=sorted(r['scope']+':'+r['name'] for r in imports if not r['used_by']))
def f15(s):
    return dict(source=f'import abc\nimport os\nimport json as j\nfrom typing import List\nX = None # type: abc.ABC\nvalue: "List[int]" = []\ndef f(os):\n    local = j.dumps({{"seed": {s}}})\n    return os\n')
task('MP15','python_import_usage','reasoning4',[('engines/ordinary',component('ordinary','ordinary_uses')),('engines/annotations',component('annotations','annotation_uses')),('engines/comments',component('comments','type_comment_uses')),('engines/analysis',component('analysis','import_usage_join',['inputs/case.json',output('ordinary'),output('annotations'),output('comments')]))],f15)

@operation('overload_signatures', '''输入含overloads:[字符串]，每项为合法Python函数签名，如"f(x: int, *, strict: bool = False) -> str"，不带def关键字、结尾冒号或函数体；参数注解中的冒号保留。使用有限Python签名语法，不执行默认值。返回{overloads:[{name,parameters:[{name,kind:posonly/positional/vararg/kwonly/kwarg,annotation:str或null,default:str或null}],returns:str或null}]}保留重载/参数顺序。注解和默认值用Python3.11 ast.unparse标准化。无默认值与默认None不同。''')
def overload_signatures(p,c):
    out=[]
    for s in rows(raw(p),'overloads'):
        try:tree=ast.parse('def '+text(s)+':\n    pass\n')
        except SyntaxError as e:raise ValueError('bad signature') from e
        require(len(tree.body)==1 and isinstance(tree.body[0],ast.FunctionDef)); f=tree.body[0]; require(len(f.body)==1 and isinstance(f.body[0],ast.Pass)); args=f.args; ps=[]; positional=args.posonlyargs+args.args; defaults=[None]*(len(positional)-len(args.defaults))+args.defaults
        def add(a,kind,default):ps.append(dict(name=a.arg,kind=kind,annotation=ast.unparse(a.annotation) if a.annotation else None,default=ast.unparse(default) if default is not None else None))
        for i,(a,b) in enumerate(zip(positional,defaults)):add(a,'posonly' if i<len(args.posonlyargs) else 'positional',b)
        if args.vararg:add(args.vararg,'vararg',None)
        for a,b in zip(args.kwonlyargs,args.kw_defaults):add(a,'kwonly',b)
        if args.kwarg:add(args.kwarg,'kwarg',None)
        out.append(dict(name=f.name,parameters=ps,returns=ast.unparse(f.returns) if f.returns else None))
    return dict(overloads=out)

def doc_objects(d):
    xs={x['id']:x for x in unique(rows(d,'objects'))}
    for x in xs.values():string(x,'doc',True); string(x,'namespace'); obj(field(x,'aliases')); require(all(a in xs for a in rows(x,'mro')))
    return xs
@operation('parameter_docs', '''输入含objects:[{id,doc:str,namespace:str,aliases:object,mro:[对象ID]}]。解析每份doc的行，支持":param name: 描述"、":param TYPE name: 描述"、":type name: TYPE"。TYPE可有空白和括号，括号必须配平；name为Python标识符。不支持续行，非上述前缀行忽略，坏指令ValueError。重复param/type报错；显式:type覆盖行内TYPE；仅type无param也保留，description=""。返回{docs:{对象ID:[{name,type:str或null,description}]按name}}。''')
def parameter_docs(p,c):
    result={}
    for id_,o in doc_objects(raw(p)).items():
        params={}; types={}
        for line in o['doc'].splitlines():
            line=line.strip()
            if line.startswith(':param '):
                m=re.fullmatch(r':param (.+?):\s*(.*)',line); require(m is not None); spec,desc=m.groups(); parts=spec.rsplit(None,1); name=parts[-1]; require(name.isidentifier() and name not in params); typ=parts[0] if len(parts)==2 else None; params[name]=(desc,typ)
            elif line.startswith(':type '):
                m=re.fullmatch(r':type ([A-Za-z_]\w*):\s*(.+)',line); require(m is not None and m[1] not in types); types[m[1]]=m[2]
        out=[]
        for name in sorted(set(params)|set(types)):
            desc,inline=params.get(name,('',None)); typ=types.get(name,inline)
            if typ is not None:
                balance=0
                for ch in typ:
                    if ch=='(':balance+=1
                    if ch==')':balance-=1
                    require(balance>=0)
                require(balance==0)
            out.append(dict(name=name,type=typ,description=desc))
        result[id_]=out
    return dict(docs=result)
@operation('inherited_doc', '''输入同parameter_docs且含target。候选顺序为target再其mro（输入已给定合法继承线性化，不计算C3）；取首个doc.strip非空对象。返回{provider:id或null,namespace:str或null,aliases:该提供者别名表}。aliases键为标识符、值为非空限定名称；无文档则aliases={}。不能用子类namespace解析父类文档。''')
def inherited_doc(p,c):
    d=raw(p); xs=doc_objects(d); target=xs[string(d,'target')]; chosen=next((xs[x] for x in [d['target']]+target['mro'] if xs[x]['doc'].strip()),None)
    if not chosen:return dict(provider=None,namespace=None,aliases={})
    for k,v in chosen['aliases'].items():require(k.isidentifier());text(v)
    return dict(provider=chosen['id'],namespace=chosen['namespace'],aliases=chosen['aliases'])
@operation('api_documentation', '''输入依次overload_signatures、parameter_docs、inherited_doc。选择provider的参数文档，仅替换type中未被点号紧邻的独立标识符，若标识符存在于provider.aliases则换为对应限定名；不改已限定名，也不替换描述正文。返回{overloads:上游重载,provider,namespace,parameters:[{name,type,description}]}；无provider时parameters=[]。''')
def api_documentation(p,c):
    sig=raw(p); docs=obj(field(raw(p,1),'docs')); provider=raw(p,2); out=[]
    if provider['provider'] is not None:
        for r in seq(docs[provider['provider']]):
            typ=r['type']; aliases=provider['aliases']
            if typ is not None:typ=re.sub(r'(?<![\w.])[A-Za-z_]\w*(?![\w.])',lambda m:aliases.get(m[0],m[0]),typ)
            out.append({**r,'type':typ})
    return dict(overloads=rows(sig,'overloads'),provider=provider['provider'],namespace=provider['namespace'],parameters=out)
def f16(s):
    return dict(overloads=['f(x: int, /, *, strict: bool = False) -> str','f(x: list[str], y = None) -> dict[str, int]'],target='Child',objects=[dict(id='Base',doc=f':param dict(str, str) x: mapping {s}\n:param y: optional\n:type y: Item',namespace='base',aliases=dict(Item='base.Item'),mro=[]),dict(id='Child',doc='',namespace='child',aliases=dict(Item='child.Item'),mro=['Base'])])
task('MP16','api_documentation_merge','context8',[('signatures',component('signatures','overload_signatures')),('parameters',component('parameters','parameter_docs')),('inheritance',component('inheritance','inherited_doc')),('document',component('document','api_documentation',[output('signatures'),output('parameters'),output('inheritance')]))],f16)

@operation('multipart_parts', '''输入{fields:object,files:{安全相对路径:字节hex},boundary:仅字母数字短横线非空str}。字段名只允许[A-Za-z0-9_.-]+。字段值为str，或含filename/content/mimetype的非空对象；content若存在必须str且优先于filename文件读取。纯str为text/plain，无文件名；对象content为inline，filename存在则取basename；仅filename则从files读取并base64编码。显式mimetype优先；否则filename后缀.txt/.json/.jpg映射text/plain/application/json/image/jpeg，其余application/octet-stream（无filename inline同此）。返回{parts:[{name,filename:str或null,mimetype,encoding:raw/base64,hex}]}按name排序。文件名只允许安全路径的basename字符[A-Za-z0-9_.-]+，MIME符合token/token；缺文件或空子对象ValueError。''')
def multipart_parts(p,c):
    d=raw(p); fields=obj(field(d,'fields')); fs=obj(field(d,'files')); out=[]
    for name,v in sorted(fields.items()):
        require(re.fullmatch(r'[A-Za-z0-9_.-]+',name) is not None); filename=None; encoding='raw'
        if type(v) is str: mime='text/plain'; data=v.encode()
        else:
            obj(v); require(v and ('content' in v or 'filename' in v)); filename=v.get('filename')
            if filename is not None:
                safe_path(filename); filename=PurePosixPath(filename).name; require(re.fullmatch(r'[A-Za-z0-9_.-]+',filename) is not None)
            if 'content' in v:data=text(v['content'],True).encode()
            else:
                path=safe_path(string(v,'filename')); data=bytes.fromhex(text(fs[path],True)); encoding='base64'
            mime=v['mimetype'] if 'mimetype' in v else {'.txt':'text/plain','.json':'application/json','.jpg':'image/jpeg'}.get(PurePosixPath(filename).suffix.lower() if filename else '', 'application/octet-stream')
            text(mime); require(re.fullmatch(r'[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+',mime) is not None)
        out.append(dict(name=name,filename=filename,mimetype=mime,encoding=encoding,hex=data.hex()))
    return dict(parts=out)
@operation('multipart_encoding', '''输入为multipart_parts。raw部件保留原字节；base64部件对字节编码并每76个ASCII字符折行，行间CRLF，无额外末尾CRLF。返回{parts:[在每个部件原字段外增加payload_hex]}，保留顺序，未知encoding报错。''')
def multipart_encoding(p,c):
    out=[]
    for r in rows(raw(p),'parts'):
        data=bytes.fromhex(string(r,'hex',True)); mode=string(r,'encoding'); require(mode in ('raw','base64'))
        if mode=='base64':
            b64=base64.b64encode(data); data=b'\r\n'.join(b64[i:i+76] for i in range(0,len(b64),76))
        out.append({**r,'payload_hex':data.hex()})
    return dict(parts=out)
@operation('multipart_body', '''输入依次原快照、multipart_encoding。boundary仅[A-Za-z0-9-]+，若字节串出现在任一payload报ValueError。每part写"--boundary\\r\\n"，文件base64时先写"Content-Transfer-Encoding: base64\\r\\n"，再Content-Type行，再Content-Disposition行，其格式为form-data; name="字段名"并可附; filename="文件名"，随后CRLF空行、载荷、CRLF；最后"--boundary--\\r\\n"。返回{content_type:"multipart/form-data; boundary=...",body_hex}。不启动HTTP或使用私有随机boundary。''')
def multipart_body(p,c):
    d=raw(p); boundary=string(d,'boundary'); require(re.fullmatch(r'[A-Za-z0-9-]+',boundary) is not None); out=bytearray()
    for r in rows(raw(p,1),'parts'):
        data=bytes.fromhex(string(r,'payload_hex',True)); require(boundary.encode() not in data); out.extend(('--'+boundary+'\r\n').encode())
        if r['encoding']=='base64':out.extend(b'Content-Transfer-Encoding: base64\r\n')
        header='Content-Type: '+r['mimetype']+'\r\nContent-Disposition: form-data; name="'+r['name']+'"'
        if r['filename'] is not None:header+='; filename="'+r['filename']+'"'
        out.extend((header+'\r\n\r\n').encode()); out.extend(data); out.extend(b'\r\n')
    out.extend(('--'+boundary+'--\r\n').encode()); return dict(content_type='multipart/form-data; boundary='+boundary,body_hex=out.hex())
def f17(s):return dict(fields=dict(title=f'hello {s}',attachment=dict(filename='data/a.bin'),inline=dict(filename='note.txt',content='é text')),files={'data/a.bin':bytes(range(128)).hex()},boundary=f'BenchBoundary{s}')
task('MP17','multipart_encoding','context8',[('parts',component('parts','multipart_parts')),('encoding',component('encoding','multipart_encoding',[output('parts')])),('body',component('body','multipart_body',['inputs/case.json',output('encoding')]))],f17)

@operation('manifest_inventory', '''输入{files:[{path,kind:file/symlink,hex:str,target:str或null}],manifest:str或null,build_ignore:[glob]或null}。普通文件hex必须合法；symlink仅记录且永不归档，其target必须安全相对路径。路径唯一，根目录外路径/反斜线/冒号/./..非法。返回{files:[普通文件的{path,hex}]按path,symlinks:[路径排序]}。不跟随真实符号链接。''')
def manifest_inventory(p,c):
    d=raw(p); out=[]; links=[]
    for r in unique(rows(d,'files'),'path'):
        path=safe_path(r['path']); kind=string(r,'kind'); require(kind in ('file','symlink'))
        if kind=='symlink':safe_path(string(r,'target')); links.append(path)
        else:
            hx=string(r,'hex',True); bytes.fromhex(hx); out.append(dict(path=path,hex=hx))
    return dict(files=sorted(out,key=lambda x:x['path']),symlinks=sorted(links))
@operation('manifest_selection', '''输入依次原快照、manifest_inventory。manifest与build_ignore不可同时非null。manifest=null时默认选全部普通文件，再用build_ignore的fnmatchcase(完整相对路径,pattern)排除。manifest非null时从空集开始按行执行4种有限指令：include PATTERN/exclude PATTERN匹配完整路径；recursive-include DIR PATTERN匹配DIR/下任意深度basename；global-exclude PATTERN匹配basename。空行/#注释忽略，未知语法报错。最后无条件排除.git目录及任何层级.git子目录、*.pyc、MANIFEST.in自身。返回{selected:[路径排序]}。fnmatch的*可跨/；不依赖distlib。''')
def manifest_selection(p,c):
    d=raw(p); paths={x['path'] for x in rows(raw(p,1),'files')}; manifest=field(d,'manifest'); ignore=field(d,'build_ignore'); require(manifest is None or ignore is None); chosen=set(paths) if manifest is None else set()
    if manifest is not None:
        for line in text(manifest,True).splitlines():
            line=line.strip()
            if not line or line.startswith('#'):continue
            bits=line.split(); require(bits)
            if bits[0] in ('include','exclude','global-exclude'):
                require(len(bits)==2); op,pattern=bits; matches={x for x in paths if fnmatch.fnmatchcase(PurePosixPath(x).name if op=='global-exclude' else x,pattern)}
            else:
                require(bits[0]=='recursive-include' and len(bits)==3); _,directory,pattern=bits; safe_path(directory); matches={x for x in paths if x.startswith(directory+'/') and fnmatch.fnmatchcase(PurePosixPath(x).name,pattern)}; op='include'
            if op=='include':chosen|=matches
            else:chosen-=matches
    elif ignore is not None:
        for pattern in seq(ignore):chosen={x for x in chosen if not fnmatch.fnmatchcase(x,text(pattern))}
    chosen={x for x in chosen if '.git' not in x.split('/') and not x.endswith('.pyc') and PurePosixPath(x).name!='MANIFEST.in'}
    return dict(selected=sorted(chosen))
@operation('manifest_archive', '''输入依次manifest_inventory、manifest_selection。按selected顺序查原字节，输出{entries:[{path,size,sha256}],total_bytes}。selected必须无重复且每项在普通文件清单中；hash针对bytes不是hex文本。未选择文件与symlink不得加入。''')
def manifest_archive(p,c):
    fs={x['path']:bytes.fromhex(x['hex']) for x in rows(raw(p),'files')}; selected=rows(raw(p,1),'selected'); require(len(selected)==len(set(selected)) and set(selected)<=fs.keys()); entries=[dict(path=x,size=len(fs[x]),sha256=hashlib.sha256(fs[x]).hexdigest()) for x in selected]; return dict(entries=entries,total_bytes=sum(x['size'] for x in entries))
def f18(s):
    paths=['plugins/a.py','plugins/tests/t.py','docs/a.txt','README.md','.git/config','plugins/a.pyc','MANIFEST.in']; return dict(files=[dict(path=x,kind='file',hex=(x+str(s)).encode().hex(),target=None) for x in paths]+[dict(path='link',kind='symlink',hex='',target='README.md')],manifest='include README.md\nrecursive-include plugins *.py\nexclude plugins/tests/*\ninclude .git/config\n' if s%2 else None,build_ignore=None if s%2 else ['docs/*'])
task('MP18','collection_manifest','linux2',[('products/inventory',component('inventory','manifest_inventory')),('products/selection',component('selection','manifest_selection',['inputs/case.json',output('inventory')])),('products/archive',component('archive','manifest_archive',[output('inventory'),output('selection')]))],f18)

def module_table(d):
    modules=obj(field(d,'modules')); mapping={}
    for path,source in modules.items():
        safe_path(path); require(path.endswith('.py')); text(source,True); name=path[:-3].replace('/','.'); name=name[:-9] if name.endswith('.__init__') else ('' if name=='__init__' else name); require(name not in mapping); mapping[name]=path
    require(string(d,'entry') in modules); return modules,mapping
@operation('module_import_scan', '''输入{modules:{相对.py路径:源码},entry:存在的入口路径,externals:[允许外部模块名],aliases:{完整导入名:允许外部模块名}}。只做AST静态import/from，不执行源码；from*禁止。对from X import y先尝试X.y存在本地模块，否则依赖X；相对from根据当前package解析，超出根报错；import X依赖X。每个包__init__.py作为该包模块。返回{imports:{路径:[规范模块名去重排序]},module_paths:{模块名:路径}}。空根__init__.py模块名为""。''')
def module_import_scan(p,c):
    d=raw(p); modules,mapping=module_table(d); out={}
    for path,source in modules.items():
        try:tree=ast.parse(source)
        except SyntaxError as e:raise ValueError('bad module source') from e
        name=next(k for k,v in mapping.items() if v==path); package=name.split('.') if path.endswith('/__init__.py') else name.split('.')[:-1]; refs=set()
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):refs.update(a.name for a in n.names)
            elif isinstance(n,ast.ImportFrom):
                require(all(a.name!='*' for a in n.names))
                if n.level:
                    require(n.level<=len(package)); base='.'.join(package[:len(package)-n.level+1]+([n.module] if n.module else []))
                else:base=n.module or ''
                for a in n.names:
                    child=(base+'.' if base else '')+a.name; refs.add(child if child in mapping else base)
        out[path]=sorted(refs)
    return dict(imports=out,module_paths=mapping)
@operation('module_dependency_closure', '''输入依次原模块输入、module_import_scan。从entry做可重复BFS：本地依赖加入对应.py，且加入所有存在的父package __init__.py；循环合法。外部模块只在externals精确命中或首段命中时允许，aliases先做精确名转换再按外部验证；未知模块ValueError。返回{paths:所有所需路径排序,external:[实际外部规范名排序]}。不能导入/执行候选源码来发现依赖。''')
def module_dependency_closure(p,c):
    d=raw(p); scan=raw(p,1); mapping=obj(field(scan,'module_paths')); imports=obj(field(scan,'imports')); allowed=set(rows(d,'externals')); aliases=obj(field(d,'aliases')); pending=[string(d,'entry')]; seen=set(); external=set()
    while pending:
        path=pending.pop(0)
        if path in seen:continue
        seen.add(path)
        for parent in PurePosixPath(path).parents:
            if str(parent)=='.':continue
            init=str(parent/'__init__.py')
            if init in d['modules'] and init not in seen:pending.append(init)
        for name in seq(imports[path]):
            if name in mapping:pending.append(mapping[name]);continue
            target=aliases.get(name,name); require(target in allowed or target.split('.')[0] in allowed,'unknown module '+name); external.add(target)
    return dict(paths=sorted(seen),external=sorted(external))
@operation('module_zip', '''输入依次原模块输入、module_dependency_closure。将paths对应源码UTF8字节加入ZIP_STORED档案；如果根__init__.py缺失则增加空根__init__.py。ZIP项按路径排序，固定时间1980-01-01 00:00:00、create_system=3、external_attr=0o644<<16、无注释。返回{paths:[ZIP路径顺序],zip_hex,sha256:ZIP字节摘要,external:上游external}。不存在的源路径/重复paths报ValueError。不包含所有未使用模块。''')
def module_zip(p,c):
    d=raw(p); closure=raw(p,1); paths=rows(closure,'paths'); require(len(paths)==len(set(paths))); content={x:string(d['modules'],x,True).encode() for x in paths}; content.setdefault('__init__.py',b''); buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_STORED) as z:
        for path,data in sorted(content.items()):
            info=zipfile.ZipInfo(path,(1980,1,1,0,0,0)); info.create_system=3; info.external_attr=0o644<<16; info.compress_type=zipfile.ZIP_STORED; z.writestr(info,data)
    data=buf.getvalue(); return dict(paths=sorted(content),zip_hex=data.hex(),sha256=hashlib.sha256(data).hexdigest(),external=rows(closure,'external'))
def f19(s):return dict(modules={'main.py':f'import pkg.a\n# {s}\n','pkg/__init__.py':'from . import b\n','pkg/a.py':'from . import b\nimport six.moves.urllib.parse\n','pkg/b.py':'from . import a\nimport json\n','unused.py':'print("unused")'},entry='main.py',externals=['json','urllib'],aliases={'six.moves.urllib.parse':'urllib.parse'})
task('MP19','module_dependency_zip','reasoning4',[('engines/scanner',component('scanner','module_import_scan')),('engines/dependencies',component('dependencies','module_dependency_closure',['inputs/case.json',output('scanner')])),('engines/payload',component('payload','module_zip',['inputs/case.json',output('dependencies')]))],f19)

@operation('feature_schema', '''输入{flags:[{id,variants:[{id,attachment:任意有限JSON}],rules:[{id,segment:str,variant:str}]}],segments:[{id}],old_snapshot:object}。flag/segment ID各自唯一，variant/rule在所属flag内唯一，均非空str。只检查形状/基本类型，不在此阶段拒绝悬空segment/variant。返回{flags:原flags深拷贝,segments:原segments深拷贝}；旧快照不在此改动。''')
def feature_schema(p,c):
    d=raw(p); flags=unique(rows(d,'flags')); segments=unique(rows(d,'segments')); obj(field(d,'old_snapshot'))
    for f in flags:
        for v in unique(rows(f,'variants')):field(v,'attachment')
        for r in unique(rows(f,'rules')):string(r,'segment'); string(r,'variant')
    return dict(flags=flags,segments=segments)
@operation('feature_attachments', '''输入同feature_schema。每个variant.attachment保留任意有限嵌套JSON，包括数组/null/布尔；生成{attachments:{flag_id:{variant_id:{value:原attachment,canonical:紧凑规范JSON字符串}}}}。不把嵌套对象转成Go样式map文本，不丢数字/布尔类型。''')
def feature_attachments(p,c):
    out={}
    for f in unique(rows(raw(p),'flags')):out[f['id']]={v['id']:dict(value=field(v,'attachment'),canonical=canonical(v['attachment'])) for v in unique(rows(f,'variants'))}
    return dict(attachments=out)
@operation('feature_references', '''输入为feature_schema结果。先检查所有flag的所有rule的segment引用，按flag/rule ID排序遇首个缺失返回{ok:false,error:{kind:"segment",flag,rule,target}}；全部segment有效后才检查variant引用，variant只在所属flag内查。全部有效返回{ok:true,error:null}。错误是合法业务拒绝，不抛ValueError；禁止在schema阶段混淆此边界。''')
def feature_references(p,c):
    d=raw(p); segments={x['id'] for x in rows(d,'segments')}; flags=sorted(rows(d,'flags'),key=lambda x:x['id'])
    for kind in ['segment','variant']:
        for f in flags:
            valid=segments if kind=='segment' else {x['id'] for x in f['variants']}
            for r in sorted(f['rules'],key=lambda x:x['id']):
                if r[kind] not in valid:return dict(ok=False,error=dict(kind=kind,flag=f['id'],rule=r['id'],target=r[kind]))
    return dict(ok=True,error=None)
@operation('feature_snapshot', '''输入依次原输入、feature_schema、feature_attachments、feature_references。引用失败时原子回退返回{committed:false,snapshot:原old_snapshot,error:上游error,export:null}。成功时构造snapshot={flags:[按id的{id,variants:[按id的{id,attachment:从attachments读取value}],rules:[按id原rule]}],segments:[按id原segment]}，返回{committed:true,snapshot,error:null,export:该snapshot紧凑规范JSON字符串}。不能先写入部分flag再发现悬空引用。''')
def feature_snapshot(p,c):
    d=raw(p); schema=raw(p,1); attach=raw(p,2)['attachments']; references=raw(p,3)
    if not references['ok']:return dict(committed=False,snapshot=obj(field(d,'old_snapshot')),error=references['error'],export=None)
    flags=[dict(id=f['id'],variants=[dict(id=v['id'],attachment=attach[f['id']][v['id']]['value']) for v in sorted(f['variants'],key=lambda x:x['id'])],rules=sorted(f['rules'],key=lambda x:x['id'])) for f in sorted(schema['flags'],key=lambda x:x['id'])]; snapshot=dict(flags=flags,segments=sorted(schema['segments'],key=lambda x:x['id']))
    return dict(committed=True,snapshot=snapshot,error=None,export=canonical(snapshot))
def f20(s):return dict(flags=[dict(id=f'f{s}-{i}',variants=[dict(id='on',attachment=dict(enabled=True,nested=[i,None]))],rules=[dict(id='r',segment='s0' if s%3 else 'missing',variant='on')]) for i in range(4)],segments=[dict(id='s0')],old_snapshot=dict(version=s,flags=[]))
task('MP20','feature_config_snapshot','multistage4',[('domains/schema',component('schema','feature_schema')),('domains/attachments',component('attachments','feature_attachments')),('views/references',component('references','feature_references',[output('schema')])),('views/snapshot',component('snapshot','feature_snapshot',['inputs/case.json',output('schema'),output('attachments'),output('references')]))],f20)

@operation('playlist_replace', '''输入{tracks:[{id,title,artist,path,duration:非负有限秒数}],playlist:{id,name,track_ids:[id],track_count:int,duration:数},replacement:[track_id],criteria:object}。track ID唯一，replacement中未知ID报错，重复轨道允许且保持顺序。完整替换旧列表，不追加；返回{playlist:{id,name,track_ids:replacement,track_count:长度,duration:按出现次数累加原duration},tracks:[replacement对应原轨道]}。旧统计值允许过时，不参与新统计。标题/艺人/path可为空串，但不允许CR/LF注入M3U行。''')
def playlist_replace(p,c):
    d=raw(p); tracks={x['id']:x for x in unique(rows(d,'tracks'))}; pl=obj(field(d,'playlist')); string(pl,'id'); string(pl,'name',True); rows(pl,'track_ids')
    for r in tracks.values():
        require(number(field(r,'duration'))>=0)
        for k in ['title','artist','path']:v=string(r,k,True);require('\n' not in v and '\r' not in v)
    ids=rows(d,'replacement'); require(all(x in tracks for x in ids)); selected=[tracks[x] for x in ids]
    return dict(playlist=dict(id=pl['id'],name=pl['name'],track_ids=ids,track_count=len(ids),duration=sum(x['duration'] for x in selected)),tracks=selected)
@operation('playlist_query', '''输入含criteria:{filters:[{field,op,value}],limit:int1..100}。字段仅id/name/track_count/duration，op仅eq/ne/gt/ge/lt/le；id/name的value必须str且只支持eq/ne，统计字段value为非负有限数。所有条件AND连接，顺序保持输入，值使用SQL占位符，不拼接。返回{sql:"SELECT id FROM playlists"+可选" WHERE field OP ? AND ..."+" ORDER BY id LIMIT ?",params:[原values...,limit]}。空filters合法，不支持用户自由SQL。''')
def playlist_query(p,c):
    d=obj(field(raw(p),'criteria')); limit=ints(d,'limit',1); require(limit<=100); operators={'eq':'=','ne':'!=','gt':'>','ge':'>=','lt':'<','le':'<='}; parts=[]; params=[]
    for r in rows(d,'filters'):
        f=string(r,'field'); op=string(r,'op'); v=field(r,'value'); require(f in ('id','name','track_count','duration') and op in operators)
        if f in ('id','name'):text(v,True);require(op in ('eq','ne'))
        else:require(number(v)>=0)
        parts.append(f+' '+operators[op]+' ?'); params.append(v)
    return dict(sql='SELECT id FROM playlists'+(' WHERE '+' AND '.join(parts) if parts else '')+' ORDER BY id LIMIT ?',params=params+[limit])
@operation('playlist_m3u', '''输入为playlist_replace结果。返回{m3u:str}，准确顺序：#EXTM3U换行、#PLAYLIST:名称换行；每条出现的track写#EXTINF:整数秒,artist - title换行再path换行。秒数用Decimal(str(duration))按ROUND_HALF_UP四舍五入（2.5→3），不能用Python的银行家round。空列表仍保留头部两行。playlist.name禁止CR/LF。''')
def playlist_m3u(p,c):
    from decimal import Decimal,ROUND_HALF_UP
    d=raw(p); name=string(d['playlist'],'name',True); require('\n' not in name and '\r' not in name); lines=['#EXTM3U','#PLAYLIST:'+name]
    for t in rows(d,'tracks'):
        duration=int(Decimal(str(number(t['duration']))).quantize(Decimal('1'),rounding=ROUND_HALF_UP)); lines.extend([f"#EXTINF:{duration},{t['artist']} - {t['title']}",t['path']])
    return dict(m3u='\n'.join(lines)+'\n')
def f21(s):return dict(tracks=[dict(id=f't{i}',title=f'Title {s}-{i}',artist='A',path=f'music/{i}.mp3',duration=i+.5) for i in range(8)],playlist=dict(id='p',name='Mix',track_ids=['t0'],track_count=99,duration=999),replacement=['t3','t1','t3','t7'],criteria=dict(filters=[dict(field='track_count',op='ge',value=2),dict(field='name',op='ne',value="O'Reilly")],limit=10))
task('MP21','playlist_query_export','context8',[('playlist',component('playlist','playlist_replace')),('query',component('query','playlist_query')),('export',component('export','playlist_m3u',[output('playlist')]))],f21)
