"""Rebuild the four PNG/SVG figures from public, de-identified JSON only."""
from pathlib import Path
import json,sys,math,statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
D=json.loads((ROOT/'metrics.json').read_text(encoding='utf-8'))
TIMELINES=json.loads((ROOT/'native-timeline-data.json').read_text(encoding='utf-8'))
PHASES=json.loads((ROOT/'e2e-phases.json').read_text(encoding='utf-8'))
OUT=ROOT/'figures';OUT.mkdir(exist_ok=True)
available={f.name for f in font_manager.fontManager.ttflist}
font=next((f for f in ['Microsoft YaHei','Noto Sans CJK SC','Source Han Sans SC','WenQuanYi Zen Hei'] if f in available),'DejaVu Sans')
plt.rcParams.update({'font.family':font,'font.size':10,'axes.titlesize':12,'axes.labelsize':10,'axes.unicode_minus':False,'svg.fonttype':'path','svg.hashsalt':'dsh-latte-original12-20261115','axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','axes.facecolor':'white'})
COLORS={'single':'#0072B2','multi':'#D55E00'}
TASKS=['TP','DBG'];NAMES={'TP':'模块扩展 TP','DBG':'信号库调试 DBG'}
def cells(t,a):return sorted([c for c in D['cells'] if c['task_id']==t and c['condition']==a],key=lambda c:c['replicate'])
def save(fig,name,caption):
 fig.text(.04,.018,caption,fontsize=9,color='#404040',va='bottom')
 for ext in ['png','svg']:fig.savefig(OUT/(name+'.'+ext),dpi=300,bbox_inches='tight',pad_inches=.16,metadata={'Date':'2026-11-15','Creator':'Matplotlib; DSH LATTE original-task paired study'})
 svg=OUT/(name+'.svg');svg.write_bytes(b'\n'.join(line.rstrip(b' \t\r') for line in svg.read_bytes().split(b'\n')))
 plt.close(fig)
def clean(ax):ax.set_axisbelow(True);ax.grid(axis='y',color='#E5E5E5',linewidth=.65)
specs=[('accuracy',100,'A  功能测试通过率：越高越好','功能测试通过率（%）',lambda x:f'{x:.1f}%'),('e2e_sec',1,'B  完整 E2E：越低越快','每 trial 完整 E2E（秒）',lambda x:f'{x:.1f}'),('total_tokens',.001,'C  全部父子 tokens：越低越省','每 trial 输入＋输出（千 tokens）',lambda x:f'{x:.1f}K'),('estimated_provider_schedule_usd',1,'D  模型费用估算：越低越省','每 trial 费用估算（USD，周末价）',lambda x:f'${x:.4f}')]
fig,axes=plt.subplots(2,2,figsize=(11,8.3));fig.subplots_adjust(top=.87,bottom=.15,hspace=.42,wspace=.28)
fig.suptitle('同模型、同总预算下：多 Agent 的质量与开销分开看',fontsize=15,y=.98)
fig.legend([Patch(facecolor=COLORS[a]) for a in ['single','multi']],['S 严格单 Agent','M 显式两子参考分工'],loc='upper center',bbox_to_anchor=(.5,.94),ncol=2,frameon=False)
for ax,(key,scale,title,ylabel,fmt) in zip(axes.flat,specs):
 top=0
 for i,task in enumerate(TASKS):
  paired=[]
  for j,arm in enumerate(['single','multi']):
   vals=[c[key]*scale for c in cells(task,arm)];x=i+(-.18 if j==0 else .18);mean=statistics.mean(vals);sd=statistics.stdev(vals)
   ax.bar(x,mean,.30,color=COLORS[arm],alpha=.77,zorder=2);ax.errorbar(x,mean,yerr=sd,color='#222222',capsize=4,linewidth=1,zorder=4)
   xs=[x+v for v in [-.055,0,.055]];ax.scatter(xs,vals,color=COLORS[arm],edgecolors='white',linewidths=.7,s=30,zorder=5);paired.append((xs,vals))
   ax.annotate(fmt(mean),(x,max(mean+sd,max(vals))),xytext=(0,7),textcoords='offset points',ha='center',fontsize=9)
   top=max(top,max(vals),mean+sd)
  for rep in range(3):ax.plot([paired[0][0][rep],paired[1][0][rep]],[paired[0][1][rep],paired[1][1][rep]],color='#777777',alpha=.45,linewidth=.8,zorder=3)
 ax.set_title(title,loc='left');ax.set_ylabel(ylabel);ax.set_xticks([0,1],[NAMES[t] for t in TASKS]);ax.set_xlabel('任务（每条件各3次）');ax.set_ylim(0,110 if key=='accuracy' else top*1.25);clean(ax)
save(fig,'01-quality-and-cost','来源：全部12次原评分与去重usage。圆点＝单次，细线＝同题同重复配对，误差线＝样本SD（非置信区间）。\nTP功能全过试次两组均0/3；DBG两组均3/3。费用是官方时段价推算，非账单。')

fig,axes=plt.subplots(2,2,figsize=(11,8));fig.subplots_adjust(top=.89,bottom=.15,hspace=.43,wspace=.28);fig.suptitle('六个配对全部保留：均值背后的变化并不一致',fontsize=15,y=.98)
pairs=D['pairs'];labels=[p['task_id']+' r'+str(p['replicate']) for p in pairs]
for ax,(key,title,ylabel) in zip(axes.flat,[('accuracy_difference_pp','A  准确率差：正值更好','M − S（百分点）'),('e2e_change_pct','B  E2E变化：负值更快','(M / S − 1) × 100（%）'),('tokens_change_pct','C  tokens变化：负值更省','(M / S − 1) × 100（%）'),('cost_change_pct','D  估算费用变化：负值更省','(M / S − 1) × 100（%）')]):
 vals=[]
 for p in pairs:
  if key=='cost_change_pct':
   s=next(c for c in cells(p['task_id'],'single') if c['replicate']==p['replicate']);m=next(c for c in cells(p['task_id'],'multi') if c['replicate']==p['replicate']);vals.append(100*(m['estimated_provider_schedule_usd']/s['estimated_provider_schedule_usd']-1))
  else:vals.append(p[key])
 ax.bar(range(6),vals,color='#777777',width=.62);ax.axhline(0,color='#222222',linewidth=1)
 for x,v in enumerate(vals):ax.annotate(f'{v:+.1f}',(x,v),xytext=(0,5 if v>=0 else -13),textcoords='offset points',ha='center',fontsize=9)
 lo=min(0,min(vals));hi=max(vals);span=max(hi-lo,10);ax.set_ylim(lo-span*.22,hi+span*.25);ax.set_xticks(range(6),labels,rotation=20);ax.set_xlabel('同题、同重复的单／多 Agent 配对');ax.set_ylabel(ylabel);ax.set_title(title,loc='left');clean(ax)
save(fig,'02-all-paired-changes','来源：6个完整配对，无成功子集筛选。TP r2的M准确率反而更低；DBG r1的M更快，其他5对E2E更长。\n每题每组仅3次，图示为探索性观察，不标统计显著性。')

fig,axes=plt.subplots(1,2,figsize=(11,4.8));fig.subplots_adjust(top=.82,bottom=.24,wspace=.32);fig.suptitle('共享四并发下：Agent阶段开销与HTTP排队都必须说明',fontsize=14,y=.99)
ax=axes[0];x=0
for task in TASKS:
 for arm in ['single','multi']:
  cs=cells(task,arm);ag=statistics.mean(c['agent_sec'] for c in cs);res=statistics.mean(c['e2e_sec']-c['agent_sec'] for c in cs)
  ax.bar(x,ag,color='#555555',width=.65);ax.bar(x,res,bottom=ag,color='#CCCCCC',width=.65);ax.text(x,ag/2,f'{ag:.1f}',ha='center',va='center',color='white',fontsize=9);ax.text(x,ag+res+3,f'{ag+res:.1f}',ha='center',fontsize=9);x+=1
ax.set_xticks(range(4),['TP S','TP M','DBG S','DBG M']);ax.set_ylabel('每 trial 墙钟均值（秒）');ax.set_xlabel('任务 × 执行条件（每格3次）');ax.set_title('A  完整E2E = Agent阶段 + 其他开销',loc='left');ax.set_ylim(0,175);clean(ax)
ax.legend([Patch(facecolor='#555555'),Patch(facecolor='#CCCCCC')],['Agent执行（含等待）','E2E其余部分'],loc='upper left',bbox_to_anchor=(0,1.19),frameon=False,ncol=2,fontsize=9)
ax=axes[1]
for i,t in enumerate(TASKS):
 for j,a in enumerate(['single','multi']):
  cs=cells(t,a);v=sum(c['http_wait_sum_sec'] for c in cs)/sum(c['requests'] for c in cs);xx=i+(-.18 if j==0 else .18);ax.bar(xx,v,.3,color=COLORS[a]);ax.text(xx,v+.06,f'{v:.3f}',ha='center',fontsize=9)
ax.set_xticks([0,1],[NAMES[t] for t in TASKS]);ax.set_xlabel('任务');ax.set_ylabel('每次HTTP请求排队均值（秒）');ax.set_title('B  FIFO网关HTTP槽等待（按请求加权）',loc='left');ax.set_ylim(0,2.4);clean(ax);ax.legend([Patch(facecolor=COLORS[a]) for a in ['single','multi']],['S','M'],frameon=False)
save(fig,'03-e2e-and-queue','来源：Harbor阶段时间、控制器完整E2E及HTTP槽事件。其他E2E是残差，含准备、评分、收尾等，不作互斥细分归因。\n本批Harbor≤4、HTTP≤4、每题HTTP≤2、Verifier1；各请求等待可重叠，不能将等待之和直接从墙钟相减。')

fig,axes=plt.subplots(3,2,figsize=(12,9));fig.subplots_adjust(top=.90,bottom=.12,hspace=.46,wspace=.16);fig.suptitle('六次M的原生父子时间线：交叠发生，净收益另由配对指标判断',fontsize=14,y=.985)
fig.legend([Patch(facecolor='#0072B2'),Patch(facecolor='#D55E00')],['模型step（含排队／网络）','工具call跨度（非纯进程区间）'],loc='upper center',bbox_to_anchor=(.5,.96),ncol=2,frameon=False)
limit=math.ceil(max(v['end_sec'] for t in TIMELINES if t['condition']=='multi' for k in ['model_steps','tool_calls'] for v in t[k])/20)*20
for ax,(task,rep) in zip(axes.flat,[(t,r) for r in range(1,4) for t in TASKS]):
 for j,role in enumerate(['parent','child-1','child-2']):
  row=next(t for t in TIMELINES if t['task_id']==task and t['replicate']==rep and t['condition']=='multi' and t['role']==role)
  ax.broken_barh([(s['start_sec'],s['end_sec']-s['start_sec']) for s in row['model_steps']],(j-.20,.21),facecolors='#0072B2')
  ax.broken_barh([(s['start_sec'],s['end_sec']-s['start_sec']) for s in row['tool_calls']],(j+.04,.13),facecolors='#D55E00')
 s=next(c for c in cells(task,'single') if c['replicate']==rep);m=next(c for c in cells(task,'multi') if c['replicate']==rep)
 ax.set_title(f"{task} r{rep}  |  完整E2E：S {s['e2e_sec']:.1f}s / M {m['e2e_sec']:.1f}s",loc='left',fontsize=10)
 ax.set_yticks([0,1,2],['父','子1','子2']);ax.invert_yaxis();ax.set_xlim(0,limit);ax.set_xlabel('相对Harbor Agent执行起点（秒）');ax.grid(axis='x',color='#E5E5E5',linewidth=.6);ax.set_axisbelow(True)
save(fig,'04-native-parent-child-timelines','来源：固定DSH原生会话step/tool的开始与完成时间；子1/2为本trial匿名身份，跨trial不对应固定角色。\n图内不含环境准备／评分／收尾；模型span含排队，工具call跨度不等于真实进程持续区间；不得据此推算纯计算加速比。')
checks=json.loads((ROOT/'functional-checks.json').read_text(encoding='utf-8'))
classes=[('TestDocumentExtensionsEval','Document'),('TestTokenizerExtensionsEval','Tokenizer'),('TestSentimentEval','Sentiment'),('TestKeywordsEval','Keywords'),('TestSummarizerEval','Summarizer'),('TestSimilarityEval','Similarity'),('TestFormatterEval','Formatter'),('TestPipelineIntegration','Pipeline')]
matrix=[];counts=[]
for cls,label in classes:
 row=[];nrow=[]
 for arm in ['single','multi']:
  rs=[r for r in checks if r['task_id']=='TP' and r['condition']==arm and r['id'].split('::')[0].split('.')[-1]==cls]
  passed=sum(r['state']=='passed' for r in rs);row.append(passed/len(rs));nrow.append((passed,len(rs)))
 matrix.append(row);counts.append(nrow)
fig,ax=plt.subplots(figsize=(7,7));fig.subplots_adjust(top=.86,bottom=.16,left=.24,right=.83)
im=ax.imshow(matrix,vmin=0,vmax=1,cmap='cividis',aspect='auto')
for i,row in enumerate(matrix):
 for j,value in enumerate(row):
  a,b=counts[i][j];ax.text(j,i,f'{a}/{b}  ({100*value:.0f}%)',ha='center',va='center',color='white' if value<.55 else '#111111',fontsize=10)
ax.set_xticks([0,1],['S 严格单Agent','M 两子参考分工']);ax.set_yticks(range(8),[label for cls,label in classes]);ax.set_xlabel('执行条件（每格3次）');ax.set_ylabel('原功能测试组');ax.set_title('模块扩展：哪些检查改善、哪些仍然失败？',fontsize=13,pad=15)
bar=fig.colorbar(im,ax=ax,fraction=.05,pad=.04);bar.set_ticks([0,.5,1],labels=['0%','50%','100%']);bar.set_label('原功能检查通过率')
save(fig,'05-functional-profile','来源：TP的原隐藏功能测试，三次检查合计；不是额外重评或修改测试。\n增量通过：Sentiment +6、Tokenizer +5、Document +2、Keywords +1，Formatter −2；Pipeline两组均12/24。\n这是检查分布的事后分解，不能将所有改善因果归于子Agent。')
print(json.dumps({'figures':5,'png':5,'svg':5,'font':font,'dpi':300,'data_source':'all12, no selection'},ensure_ascii=False))
