"""Additional task-specific contracts. All fixtures are finite normal business inputs."""
import copy

def register(add,C,R,O):
    add('N02','isolated_dimension_swap',[
        C('variable_plan','variable_plan',{'dataset':R+'/dataset','swap':R+'/swap'},"dataset.variables 是 {name:{dims:[维度名],data:[整数],attrs:字段字典}}；swap 是单个 {旧维度:新坐标变量名}。生成变量计划 {name:{dims:替换后的维度列表,data:原数据,attrs:原attrs}}，所有结果可变元数据必须与输入隔离。输入是一维同长变量，目标坐标变量存在。"),
        C('coordinate_plan','coordinate_plan',{'dataset':R+'/dataset','swap':R+'/swap'},"返回 {coords:把 swap 的目标变量加入原 coords 后排序去重,indexes:{新坐标名:目标变量的数据}}。"),
        C('new_dataset','apply_swap',{'variables':O('variable_plan'),'coordinates':O('coordinate_plan')},"返回新 {variables,coords,indexes}，对象不得通过可变 dims/attrs/coords/indexes 别名修改 payload。")],
        [dict(dataset=dict(variables={'y':dict(dims=['z'],data=[4,5],attrs={'unit':'m'}),'lev':dict(dims=['z'],data=[0,10],attrs={})},coords=[]),swap={'z':'lev'}),
         dict(dataset=dict(variables={'v':dict(dims=['x'],data=[9,8,7],attrs={'note':'v'}),'time':dict(dims=['x'],data=[1,2,3],attrs={'kind':'clock'})},coords=['time']),swap={'x':'time'}),
         dict(dataset=dict(variables={'a':dict(dims=['n'],data=[2],attrs={}),'id':dict(dims=['n'],data=[30],attrs={'s':'id'})},coords=[]),swap={'n':'id'})],'swap_immutable')
    add('N03','class_marker_mro',[
        C('linearization','c3',{'classes':R+'/classes','target':R+'/target'},"classes 是 {类名:{bases:有序直接基类列表,marks:本地标记JSON值列表}}。输入是无环且可 C3 线性化的有效类图，根类 bases=[]。返回 target 的 C3 类名列表，首项是自己。不执行用户类代码。"),
        C('local_marks','local_marks',{'classes':R+'/classes'},"返回每个类自身声明的 marks 的独立副本字典，不能把继承标记混入本地标记。"),
        C('effective_marks','merge_marks',{'mro':O('linearization'),'local':O('local_marks')},"按 mro 顺序逐类连接本地标记列表，保留同名不同参数的标记和本地列表顺序。返回 {mro,marks}。")],
        [dict(classes={'A':dict(bases=[],marks=['a']),'B':dict(bases=[],marks=['b']),'C':dict(bases=['A','B'],marks=['c'])},target='C'),
         dict(classes={'O':dict(bases=[],marks=[{'x':0}]),'A':dict(bases=['O'],marks=[{'x':1}]),'B':dict(bases=['O'],marks=[{'x':2}]),'D':dict(bases=['A','B'],marks=[])},target='D'),
         dict(classes={'R':dict(bases=[],marks=[]),'L':dict(bases=['R'],marks=['l','l']),'T':dict(bases=['L'],marks=['t'])},target='T')],'python_mro')
    booleans=[dict(id=i,a=bool(i&1),b=bool(i&2),c=bool(i&4)) for i in range(8)]
    add('N04','xor_backend_parity',[
        C('native_values','native_bool',{'ast':R+'/ast','rows':R+'/rows'},"ast 为字段名字符串，或 {op:'and'|'or'|'xor',args:[AST,...]}。args 非空，字段为非空布尔值。按布尔逻辑计算每行真假，xor 为真项数的奇偶性。返回 [bool,...]，按 rows 原顺序。"),
        C('fallback_values','fallback_bool',{'ast':R+'/ast','rows':R+'/rows'},"为不支持原生 XOR 的 SQLite 编译参数表达式（字段写成 :字段），实际执行每行。返回 {sql:可用于 SELECT(expression) 的SQLite表达式,values:[bool,...]}。允许任何语义等价表达式，不要求固定SQL文本。xor 的 fallback 必须保持奇偶性。"),
        C('query_result','xor_report',{'native':O('native_values'),'fallback':O('fallback_values'),'rows':R+'/rows'},"若两后端 values 一致，返回 {values:真假列表,selected_ids:按输入顺序选中行ID}。消费实际后端结果，不使用固定答案。")],
        [dict(ast={'op':'xor','args':['a','b','c']},rows=booleans),dict(ast={'op':'xor','args':['a','a','a','a','a']},rows=booleans),dict(ast={'op':'and','args':[{'op':'xor','args':['a','b','c']},{'op':'or','args':['a','c']}]},rows=booleans)],'boolean_truth')
    add('N05','database_timezone_dates',[
        C('backend_a','timezone_a',{'rows':R+'/rows','source':R+'/source','target':R+'/target'},"rows=[{id,local:'YYYY-MM-DDTHH:MM:SS'}]，source/target 为相对 UTC 的整数分钟偏移（±720以内）。返回 [{id,date:'YYYY-MM-DD'}]，须先从数据库本地区时间换到业务时区再取日期。"),
        C('backend_b','timezone_b',{'rows':R+'/rows','source':R+'/source','target':R+'/target'},"同 backend_a 的日期语义，用独立后端路径处理；同区时不可重复偏移。"),
        C('date_query','date_report',{'a':O('backend_a'),'b':O('backend_b'),'date':R+'/date'},"两后端一致时返回 {dates:a,selected_ids:日期等于 date 的行ID}。")],
        [dict(rows=[dict(id=1,local='2024-01-02T03:10:00'),dict(id=2,local='2024-01-02T10:00:00')],source=420,target=180,date='2024-01-01'),dict(rows=[dict(id='a',local='2024-12-31T22:30:00')],source=-120,target=180,date='2025-01-01'),dict(rows=[dict(id=9,local='2024-06-01T23:30:00')],source=120,target=120,date='2024-06-01')],'timezone_projection')
    add('N06','simultaneous_query_aliases',[
        C('symbol_tables','query_symbols',{'left':R+'/left','right':R+'/right'},"left/right 是 {tables:{alias:表名},clauses:[{alias,field,value}]}；每个 clause.alias 都在对应 tables 内。返回 {left:排序别名列表,right:排序别名列表}。"),
        C('rename_map','alias_map',{'symbols':O('symbol_tables')},"为右查询的每个原别名按字典序分配新别名 T0,T1,...，跳过左右原别名及已分配名称。返回 {原右别名:新别名}。此公开命名规则用于稳定输出；替换必须同时进行，不能串行替换导致二次改名。"),
        C('combined_query','rewrite_aliases',{'left':R+'/left','right':R+'/right','mapping':O('rename_map')},"返回 {tables:左表映射与重命名后右表映射,branches:[左clauses,按原映射同时改名的右clauses]}。保留每个 clause 的 field/value 与原顺序，两分支表示 OR，不把字符串 value 内的别名文本当引用改写。")],
        [dict(left={'tables':{'T0':'foo'},'clauses':[dict(alias='T0',field='id',value=3)]},right={'tables':{'T1':'foo','T2':'bar'},'clauses':[dict(alias='T1',field='name',value='T1'),dict(alias='T2',field='id',value=8)]}),dict(left={'tables':{'T3':'a'},'clauses':[]},right={'tables':{'T0':'b','T1':'a'},'clauses':[dict(alias='T0',field='x',value=4),dict(alias='T1',field='x',value=5)]}),dict(left={'tables':{'L':'a'},'clauses':[dict(alias='L',field='k',value=0)]},right={'tables':{'R':'a'},'clauses':[dict(alias='R',field='k',value=1)]})],'alias_identity')
    add('N07','nested_fraction_parser',[
        C('expression_ast','parse_fraction',{'latex':R+'/latex'},r"解析公开语法：整数、单字母变量、花括号/圆括号分组、+、*、^和\frac{expr}{expr}。+/*左结合，^只跟非负整数字面量；\frac保留完整分子分母。返回AST：['int',n]、['var',name]、['add'|'mul'|'div'|'pow',left,right]。无隐式乘法、所有输入合法，深度≤8。"),
        C('exact_value','eval_fraction',{'ast':O('expression_ast'),'values':R+'/values'},"使用有理数解释AST，values给每个变量整数值且所有分母非零。返回 {numerator:最简有符号整数,denominator:正整数}。"),
        C('expression_report','fraction_report',{'ast':O('expression_ast'),'value':O('exact_value')},"返回 {ast:输入AST,value:输入有理数值,text:全括号中缀表示}。int/var直接打印，add/mul/div/pow分别打印 (left+right)/(left*right)/(left/right)/(left^right)，此处斜线表示规则分隔而非输出串；每个二元节点恰有一对外括号。")],
        [dict(latex=r'\frac{\frac{a}{c}}{\frac{1}{c^2}}',values={'a':2,'c':3}),dict(latex=r'\frac{1+2}{\frac{3}{4}}',values={}),dict(latex=r'\frac{x^2+1}{2}*3',values={'x':4})],'fraction_numeric')
    add('N08','log_level_scope_restore',[
        C('level_snapshot','log_snapshot',{'initial':R+'/initial'},"initial={handler:整数阈值,loggers:{名称:整数阈值}}。返回独立拷贝，保存测试开始时等级。"),
        C('captured_records','log_capture',{'initial':R+'/initial','events':R+'/events'},"events依次为 {kind:'set',logger,level}（同时设置该logger与handler），或 {kind:'emit',logger,level,text}。日志级别>=logger阈值且>=handler阈值才捕获。返回 {state:测试末等级,captured:[捕获的text]}；不修改输入。"),
        C('restored_report','log_restore',{'snapshot':O('level_snapshot'),'capture':O('captured_records'),'next_events':R+'/next_events'},"结束时从首次快照恢复全部等级，再处理下一测试的 emit 事件。返回 {restored:快照,captured:上个测试捕获文本,next_captured:下一测试可见文本}。")],
        [dict(initial={'handler':20,'loggers':{'a':20}},events=[dict(kind='set',logger='a',level=40),dict(kind='set',logger='a',level=50),dict(kind='emit',logger='a',level=45,text='hidden')],next_events=[dict(kind='emit',logger='a',level=20,text='restored')]),dict(initial={'handler':10,'loggers':{'a':20,'b':30}},events=[dict(kind='set',logger='a',level=40),dict(kind='emit',logger='b',level=35,text='blocked'),dict(kind='emit',logger='b',level=50,text='yes')],next_events=[dict(kind='emit',logger='b',level=30,text='next')]),dict(initial={'handler':0,'loggers':{'x':0}},events=[dict(kind='emit',logger='x',level=10,text='first')],next_events=[dict(kind='emit',logger='x',level=1,text='second')])],'log_state_machine')
    from blueprints_more import register_more
    register_more(add,C,R,O)
