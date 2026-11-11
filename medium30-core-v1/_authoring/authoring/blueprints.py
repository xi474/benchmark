"""Exact public contracts, source-linked normal inputs, and task-specific models."""
TASKS={}

def comp(name, op, bindings, spec, **extra):
    return dict(name=name, op=op, bindings=bindings, spec=spec, **extra)

def add(ident, slug, components, inputs, oracle, **extra):
    TASKS[ident]=dict(id=ident,slug=slug,components=components,inputs=inputs,oracle=oracle,**extra)

R="inputs/request.json#"
O=lambda name:"outputs/"+name+".json#"

add("N01","nested_model_dependencies",[
    comp("left_dependencies","model_matrix",{"model":R+"/left"},"输入 model 是叶子 {kind:'leaf',matrix:[[0或1,...],...]}，或 {kind:'parallel'|'serial',left:模型,right:模型}。矩阵行对应输出，列对应输入。parallel 使用块对角；serial 表示先 left 后 right，结果是 right×left 的布尔乘积。返回依赖矩阵（0/1 的二维列表）。所有维度合法、矩阵非空；树深≤6，输入输出维度≤12。"),
    comp("right_dependencies","model_matrix",{"model":R+"/right"},"与 left_dependencies 相同的模型依赖规则，独立计算右子树。"),
    comp("dependency_report","join_models",{"left":O("left_dependencies"),"right":O("right_dependencies"),"kind":R+"/kind"},"按 kind=parallel/serial 组合两个矩阵。返回 {matrix:依赖矩阵,input_count:列数,output_count:行数,separable:[bool,...]}。某输出恰好依赖一个输入，且没有其他输出依赖同一输入时才 separable=true。")],
    [dict(left={"kind":"leaf","matrix":[[1]]},right={"kind":"parallel","left":{"kind":"leaf","matrix":[[1]]},"right":{"kind":"leaf","matrix":[[1]]}},kind="parallel"),
     dict(left={"kind":"leaf","matrix":[[1,0],[1,1]]},right={"kind":"leaf","matrix":[[0,1],[1,0]]},kind="serial"),
     dict(left={"kind":"parallel","left":{"kind":"leaf","matrix":[[1]]},"right":{"kind":"leaf","matrix":[[1,1],[0,1]]}},right={"kind":"leaf","matrix":[[1,0,0],[0,1,1]]},kind="serial")],"model_sets")

add("N14","bulk_sorted_set_updates",[
    comp("operation_groups","group_increments",{"initial":R+"/initial","operations":R+"/operations"},"initial 是 {set_key:{member:整数分数}}；operations 是 [{key,member,delta:整数}]。按 (key,member) 分组并按键/成员字典序返回列表，每组为 {key,member,initial:原分数或0,operations:[{index:原始0基位置,delta}]}，保留组内原顺序。"),
    comp("group_folds","fold_increments",{"groups":O("operation_groups")},"独立计算各组有序前缀和。返回列表 [{key,member,final:最终分数,results:[{index,score:本次操作后的分数}]}]，组顺序不变。"),
    comp("bulk_result","assemble_increments",{"folds":O("group_folds"),"initial":R+"/initial","count":R+"/count"},"合并分组结果。返回 {scores:[按操作原位置的分数],sets:保留未操作成员的最终集合字典}。同一成员多次增分不可用最终值回填先前操作。count 等于操作数。")],
    [dict(initial={"a":{"x":10,"untouched":7}},operations=[dict(key="a",member="x",delta=2),dict(key="b",member="y",delta=4),dict(key="a",member="x",delta=3)],count=3),
     dict(initial={"s":{"p":1}},operations=[dict(key="s",member="q",delta=6),dict(key="s",member="p",delta=-1),dict(key="s",member="q",delta=-2)],count=3),
     dict(initial={"u":{"x":4},"v":{"x":20}},operations=[dict(key="v",member="x",delta=5),dict(key="u",member="x",delta=8),dict(key="v",member="x",delta=-3),dict(key="u",member="z",delta=9)],count=4)],"sequential_increments")

add("N18","encoded_url_numbers",[
    comp("url_segments","split_url",{"url":R+"/url"},"解析合法的 scheme://host[:port]/path[?query][#anchor]。本题限定 ASCII host，无 userinfo/IPv6。返回 {scheme,host,port,path,query,anchor}；缺失 port/query/anchor 用 null，保留原始字节和空 query/anchor。path 可为空；不得 unquote。"),
    comp("numeric_target","url_target",{"parts":O("url_segments"),"segments":R+"/segments"},"依 host,port,path,query,anchor 的 URL 顺序，在给定 segments 中找到最后一个可修改连续 ASCII 数字串。合法 %XX 三字符内的数字必须屏蔽；其后的普通数字可修改。返回 {segment,start,end,text}，start/end 是对应原始段的0基半开跨度。输入保证存在可选数字。"),
    comp("modified_url","rewrite_url",{"parts":O("url_segments"),"target":O("numeric_target"),"operation":R+"/operation","count":R+"/count"},"operation=increment/decrement，count 是非负整数，输入保证结果非负。仅替换目标跨度；原字符串若有前导零，尽可能保持原宽度，超出时扩宽；原值无前导零则不补零。返回完整新 URL 字符串，其余部分逐字保持。")],
    [dict(url="http://localhost/%3A005?v=9#hold7",segments=["path"],operation="increment",count=1),
     dict(url="https://h4:8080/a09?v=%3132",segments=["path","query"],operation="decrement",count=2),
     dict(url="http://node9:80/x?y=7#z010",segments=["port","anchor"],operation="decrement",count=1),
     dict(url="https://h:89/%2F9?",segments=["path","port"],operation="increment",count=2)],"raw_url_scan")

def account(i,n,b):return i+n.ljust(20)+str(b).zfill(10)
def book(i,n,o):return i+n.ljust(20)+o
def order(b,s,k,a):return b+s+k+str(a).zfill(10)

add("N24","cobol_fixed_records",[
    comp("accounts","parse_accounts",{"text":R+"/accounts"},"按34字符定长记录解析账户，字段 ID4/姓名20/余额10。返回 [{id,name:去掉末尾填充空格,balance:整数}]，保持文件顺序。合法 ASCII 输入。"),
    comp("books","parse_books",{"text":R+"/books"},"按28字符定长记录解析图书，字段 ID4/书名20/owner4。返回 [{id,title:去掉末尾空格,owner}]，保持文件顺序。"),
    comp("orders","parse_orders",{"orders":R+"/orders"},"逐个解析22字符交易请求：buyer4/seller4/book4/amount10。返回 [{buyer,seller,book,amount:整数}]，保持请求顺序。"),
    comp("settlement","settle_books",{"accounts":O("accounts"),"books":O("books"),"orders":O("orders"),"journal":R+"/journal"},"顺序执行交易。请求中的买卖账户和书均存在，买卖方不同、正常金额且余额足够；当前 owner==seller 才成功。成功时买方余额减金额、卖方增加、owner改买方，向 journal 追加 book4+amount10+seller4+buyer4；不符所有权时三类文件不变。返回 {accounts:重编码定长串,books:重编码定长串,journal:累计交易串,statuses:['accepted'|'rejected',...]}。保持原记录顺序，姓名/书名填充20位，数值填充10位。",emit={"outputs/ACCOUNTS.DAT":{"pointer":"/accounts","format":"text"},"outputs/BOOKS.DAT":{"pointer":"/books","format":"text"},"outputs/TRANSACTIONS.DAT":{"pointer":"/journal","format":"text"}})],
    [dict(accounts=account("U001","John Doe",1000)+account("U002","Jane Smith",2000)+account("U003","Bob Wilson",1500),books=book("B001","Python Basics","U001")+book("B003","Java Tutorial","U003"),orders=[order("U001","U003","B003",20),order("U002","U001","B003",50),order("U002","U001","B001",150)],journal=""),
     dict(accounts=account("U001","A",900)+account("U002","B",800),books=book("B001","Book","U001"),orders=[order("U002","U001","B001",10),order("U002","U001","B001",10)],journal=""),
     dict(accounts=account("U001","C",300)+account("U002","D",400),books=book("B001","One","U002")+book("B002","Two","U001"),orders=[order("U001","U002","B001",40),order("U002","U001","B002",30),order("U002","U001","B001",20)],journal="B0020000000001U002U001")],"fixed_record_machine")

from blueprints_extra import register
register(add,comp,R,O)
