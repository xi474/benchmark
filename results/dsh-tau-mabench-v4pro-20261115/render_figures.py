"""Generate offline, reproducible Chinese summary figures from retained metrics."""
from pathlib import Path
import csv, hashlib, json, math, statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Patch
import numpy as np

P=Path(__file__).resolve().parent; OUT=P/'figures'; OUT.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
dump=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
source=read(P/'metrics.json')
trace=read(P/'native-timeline-data.json'); pairs=read(P/'parallel-trace-summary.json')
cells=sorted([c for c in source['cells'] if c['stage']==3],key=lambda c:(c['task_index'],c['condition']))
by={(c['task_index'],c['condition']):c for c in cells}
font=Path('C:/Windows/Fonts/msyh.ttc')
if font.exists():fm.fontManager.addfont(str(font));family=fm.FontProperties(fname=str(font)).get_name()
else:family='DejaVu Sans'
plt.rcParams.update({'font.family':family,'font.size':10,'axes.titlesize':12,'axes.labelsize':10,
    'figure.facecolor':'white','axes.facecolor':'white','axes.spines.top':False,'axes.spines.right':False,
    'axes.edgecolor':'#9CA3AF','axes.labelcolor':'#344054','text.color':'#1D2939','xtick.color':'#475467',
    'ytick.color':'#475467','axes.unicode_minus':False,'svg.fonttype':'none','savefig.facecolor':'white'})
BLUE='#356A9A';ORANGE='#C47B35';GRAY='#8F98A4';LIGHT='#E8EBEF';DARK='#344054'
palette={'single':BLUE,'multi':ORANGE}; labels={'single':'S 严格单Agent','multi':'M 受控强委派'}
groups={}
for arm in ['single','multi']:
    rows=[c for c in cells if c['condition']==arm]
    u={k:sum(c[k] for c in rows) for k in ['input_tokens','output_tokens','billing_cache_tokens','total_tokens','requests']}
    u['cache_miss_tokens']=u['input_tokens']-u['billing_cache_tokens']
    u.update(e2e_mean_sec=statistics.mean(c['e2e_sec'] for c in rows),
             agent_mean_sec=statistics.mean(c['agent_sec'] for c in rows),
             original_task_success_rate=sum(c['original_reward']==1 for c in rows)/len(rows),
             cost_weekend_usd=sum(c['estimated_weekend_usd'] for c in rows),
             cache_hit_rate=u['billing_cache_tokens']/u['input_tokens'],
             parent_tokens=sum(c['role_usage']['parent']['input_tokens']+c['role_usage']['parent']['output_tokens'] for c in rows),
             child_tokens=sum(c['role_usage']['children']['input_tokens']+c['role_usage']['children']['output_tokens'] for c in rows),
             user_tokens=sum(c['role_usage']['simulated_user']['input_tokens']+c['role_usage']['simulated_user']['output_tokens'] for c in rows))
    # Frozen peak rates / 2, matching the existing Sunday estimate. Not an invoice.
    u['cost_components_usd']={'输入缓存命中':u['billing_cache_tokens']*.022/1e6,
                             '输入缓存未命中':u['cache_miss_tokens']*.66/1e6,
                             '输出':u['output_tokens']*1.98/1e6}
    assert math.isclose(sum(u['cost_components_usd'].values()),u['cost_weekend_usd'],abs_tol=1e-12)
    groups[arm]=u
S=groups['single'];M=groups['multi'];delta_cost=M['cost_weekend_usd']-S['cost_weekend_usd']
analysis=dict(groups=groups,
    deltas_pct={k:(M[k]/S[k]-1)*100 for k in ['e2e_mean_sec','total_tokens','cost_weekend_usd']},
    extra_cost_components={k:dict(delta_usd=M['cost_components_usd'][k]-S['cost_components_usd'][k],
            fraction=(M['cost_components_usd'][k]-S['cost_components_usd'][k])/delta_cost) for k in S['cost_components_usd']},
    extra_token_roles={'parent':M['parent_tokens']-S['parent_tokens'],'children':M['child_tokens'],
                       'simulated_user':M['user_tokens']-S['user_tokens']},
    cells=cells,trace=trace,pairs=pairs,
    stage_counts={'R1_adapter_censored':4,'R2_complete_but_M_no_delegation':4,'R3_strict_paired':4},
    evidence_limit='Each R3 task×condition has one attempt; two task pairs, no significance or autonomous timing claim.',
    extra_model_requests=0,
    source_hashes={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['metrics.json','parallel-trace-summary.json','completion-audit.json']})

def clean(ax):
    ax.set_axisbelow(True);ax.grid(axis='y',color=LIGHT,linewidth=.7);ax.spines['left'].set_visible(False)
    ax.tick_params(axis='both',length=0);ax.margins(x=.22)
def finish(fig,name,footer):
    fig.text(.045,.018,footer,fontsize=9,color='#667085',va='bottom')
    fig.savefig(OUT/(name+'.png'),dpi=180,bbox_inches='tight')
    fig.savefig(OUT/(name+'.svg'),bbox_inches='tight');plt.close(fig)
def bars(ax,values,title,ylabel,fmt):
    clean(ax);x=np.arange(2);b=ax.bar(x,values,width=.48,color=[BLUE,ORANGE])
    ax.set_xticks(x,['S 单Agent','M 强委派']);ax.set_ylabel(ylabel);ax.set_title(title,loc='left',pad=16)
    ax.set_ylim(0,max(values)*1.3)
    for p,v in zip(b,values):ax.text(p.get_x()+p.get_width()/2,v+max(values)*.04,fmt(v),ha='center',fontsize=12,fontweight='bold')

fig,axes=plt.subplots(2,2,figsize=(12.4,8.5));fig.subplots_adjust(top=.83,bottom=.12,wspace=.30,hspace=.65)
fig.suptitle('DSH × τ-bench：真实并行发生了，净收益尚未出现',x=.045,y=.98,ha='left',fontsize=18,fontweight='bold')
fig.text(.045,.92,'R3 同版本对照｜原第0、2题各 S/M 一次｜V4 Pro普通｜四Harbor / HTTP4',fontsize=11,color='#667085')
bars(axes[0,0],[100,100],'准确率：原整题成功率持平','成功率（%）',lambda v:'2/2 = 100%')
axes[0,0].set_yticks([0,50,100])
bars(axes[0,1],[S['e2e_mean_sec'],M['e2e_mean_sec']],'完整E2E：均值增加26.0%','两题均值（秒）',lambda v:f'{v:.2f}')
bars(axes[1,0],[S['total_tokens']/1e6,M['total_tokens']/1e6],'tokens：累计增加35.3%','两题累计（百万tokens）',lambda v:f'{v:.3f} M')
bars(axes[1,1],[S['cost_weekend_usd'],M['cost_weekend_usd']],'费用：周末价估算增加147.3%','两题累计估算（USD）',lambda v:f'${v:.5f}')
finish(fig,'01-overview','来源：2026-11-15原score、Harbor时间与网关usage；含父/子/模拟用户。每格n=1；费用非账单；API语义准确率无原分母记N/A。')

fig,axes=plt.subplots(1,3,figsize=(14,4.9));fig.subplots_adjust(top=.75,bottom=.18,wspace=.40)
fig.suptitle('每一道配对：多Agent都通过，但两题都更慢、更贵',x=.045,y=.98,ha='left',fontsize=16,fontweight='bold')
for ax,(key,title,unit,scale,fmt) in zip(axes,[('e2e_sec','完整E2E','秒',1,lambda v:f'{v:.1f}'),
        ('total_tokens','全部tokens','千tokens',1000,lambda v:f'{v:.1f}'),
        ('estimated_weekend_usd','周末价估算费用','USD',1,lambda v:f'${v:.4f}')]):
    clean(ax);x=np.arange(2);width=.32
    for j,arm in enumerate(['single','multi']):
        vals=[by[t,arm][key]/scale for t in [0,2]]
        bs=ax.bar(x+(j-.5)*width,vals,width,color=palette[arm],label=labels[arm])
        for b,v in zip(bs,vals):ax.text(b.get_x()+b.get_width()/2,v+max(vals)*.035,fmt(v),ha='center',fontsize=9)
    ax.set_xticks(x,['第0题：换货','第2题：查询＋退货']);ax.set_title(title,loc='left');ax.set_ylabel(unit)
    ax.set_ylim(0,max(by[t,a][key]/scale for t in [0,2] for a in ['single','multi'])*1.27)
axes[0].legend(frameon=False,loc='upper left',bbox_to_anchor=(-.05,1.32),ncol=2)
finish(fig,'02-task-pairs','来源：R3四次真实试次；每个任务每条件n=1，原reward均1；不是平均后的同条件三次重复，未作显著性检验。')

fig,axes=plt.subplots(1,3,figsize=(14,5.2));fig.subplots_adjust(top=.73,bottom=.18,wspace=.43)
fig.suptitle('开销来源：父上下文未缩小，未命中输入和输出更贵',x=.045,y=.98,ha='left',fontsize=16,fontweight='bold')
ax=axes[0];clean(ax);bottom=np.zeros(2)
for key,name,color in [('parent_tokens','父Agent',BLUE),('child_tokens','子Agent',ORANGE),('user_tokens','模拟用户',GRAY)]:
    values=np.array([S[key],M[key]])/1000;ax.bar([0,1],values,.52,bottom=bottom,label=name,color=color);bottom+=values
ax.set_xticks([0,1],['S','M']);ax.set_ylabel('累计tokens（千）');ax.set_title('角色用量分解',loc='left');ax.legend(frameon=False,fontsize=9,loc='upper left',bbox_to_anchor=(-.1,1.25),ncol=3)
ax.text(.02,.97,'父 +21.1%\n子新增 96,553',transform=ax.transAxes,ha='left',va='top',fontsize=9)
ax=axes[1];clean(ax);bottom=np.zeros(2)
for name,color in [('输入缓存命中',GRAY),('输入缓存未命中',ORANGE),('输出',BLUE)]:
    vals=np.array([S['cost_components_usd'][name],M['cost_components_usd'][name]])*1000
    ax.bar([0,1],vals,.52,bottom=bottom,color=color,label=name);bottom+=vals
ax.set_xticks([0,1],['S','M']);ax.set_ylabel('周末价估算（千分之一USD）');ax.set_title('账目分量：非因果归因',loc='left');ax.legend(frameon=False,fontsize=8,loc='upper left',bbox_to_anchor=(-.1,1.25),ncol=2)
ax=axes[2];clean(ax)
parts=list(analysis['extra_cost_components']);vals=[analysis['extra_cost_components'][p]['fraction']*100 for p in parts]
ax.barh(parts,vals,color=[GRAY,ORANGE,BLUE]);ax.grid(False);ax.set_xlim(0,70);ax.set_xlabel('占新增估算费用（%）');ax.set_title('新增费用的分量占比',loc='left');ax.invert_yaxis()
for i,v in enumerate(vals):ax.text(v+1,i,f'{v:.1f}%',va='center')
finish(fig,'03-tokens-cost','输入缓存命中率 S98.42% / M95.14%；未命中tokens 10,428→43,161，输出3,048→10,234。价格沿用冻结周末档，非账单。')

fig,axes=plt.subplots(2,1,figsize=(13.2,8));fig.subplots_adjust(top=.85,bottom=.13,left=.13,right=.80,hspace=.68)
fig.suptitle('原生trace时间线：交叠只覆盖局部，业务主链仍由父推进',x=.045,y=.98,ha='left',fontsize=17,fontweight='bold')
fig.text(.045,.93,'色块为已实际发送HTTP的在途区间；浅灰为请求排队；竖刻度为业务工具；并非纯模型计算时间',fontsize=10,color='#667085')
role_y={'parent':3,'child1':2,'child2':1,'simulated_user':0}
for ax,task in zip(axes,[0,2]):
    c=next(c for c in trace['cells'] if c['task_index']==task and c['condition']=='multi')
    meta=next(c for c in pairs['cells'] if c['task_index']==task and c['condition']=='multi')
    for q in c['intervals']:
        y=role_y[q['role']];col=BLUE if y==3 else ORANGE if y in [1,2] else GRAY
        if q['wait_sec']>.005:ax.broken_barh([(q['queue_start'],q['queue_end']-q['queue_start'])],(y-.29,.12),facecolors=LIGHT)
        ax.broken_barh([(q['http_start'],q['http_end']-q['http_start'])],(y-.12,.28),facecolors=col,
                      hatch='///' if q['role']=='child2' else None,edgecolors=col,linewidth=.2)
    for t in c['tools']:
        if t['tool'].startswith('retail__'):ax.plot([t['start']],[role_y[t['role']]],marker='|',color=DARK,ms=13,mew=1)
    spawns=[t['start'] for t in c['tools'] if t['tool']=='spawn_teammate']
    last=max(m['time'] for m in c['parent_inbox_splices'])
    ax.axvline(min(spawns),ls=':',color=GRAY,lw=1);ax.axvline(last,ls='--',color=GRAY,lw=1)
    ax.axvspan(last,c['agent_sec'],color=LIGHT,alpha=.45,zorder=-2)
    ax.text(min(spawns),3.65,'两子创建',ha='center',fontsize=8)
    ax.text(last,3.45,'最后inbox拼接',ha='left',fontsize=8)
    later=next((x['time'] for x in c['communications'] if x['kind']=='customer_reveals_return_request'),None)
    if later is not None:ax.annotate('此时才公开退货要求',xy=(later,0),xytext=(later+6,-.72),fontsize=8,
                                    arrowprops=dict(arrowstyle='-',color=GRAY),ha='center')
    ax.set_yticks([3,2,1,0],['父Agent','子A','子B','模拟用户']);ax.set_ylim(-.8,3.85);ax.set_xlim(0,112)
    ax.set_xlabel('相对Harbor Agent阶段起点（秒）');ax.set_title(f'第{task}题：'+('两种商品，可互补查询' if task==0 else '同一库存，两个子重复调查'),loc='left',pad=15)
    overlap=next(x['actual_http_overlap_sec'] for x in meta['actual_http_role_overlaps'] if x['roles']==['child1','child2'])
    ax.text(1.02,.79,f'兄弟HTTP交叠\n{overlap:.2f}秒\n\ninbox后父仍运行\n{c["parent_tail_after_last_inbox_splice_sec"]:.2f}秒',
            transform=ax.transAxes,va='top',fontsize=10)
    ax.spines['left'].set_visible(False);ax.grid(axis='x',color=LIGHT,linewidth=.7);ax.set_axisbelow(True)
finish(fig,'04-native-timeline','来源：R3原生span/agent.inbox.spliced及网关dispatch→settled；时间线不含Agent阶段外约17秒E2E。排队不可直接换算成净损失。')

fig,ax=plt.subplots(figsize=(12.5,3.8));fig.subplots_adjust(top=.65,bottom=.2,left=.13,right=.97)
fig.suptitle('样本边界：12次已消费，不是12次同版本有效对照',x=.045,y=.98,ha='left',fontsize=17,fontweight='bold')
names=['R1 对话适配故障','R2 旧提示未触发M','R3 受控强委派'];colors=[GRAY,BLUE,ORANGE]
ax.barh(range(3),[4,4,4],color=colors,height=.48)
for i,t in enumerate(['4次保留；排除正常质量结论','4次完整评分；两M都0子','4次同版本配对；两M各2有工作子']):ax.text(.12,i,t,color='white',va='center',fontsize=10)
ax.set_yticks(range(3),names);ax.set_xlabel('实际付费attempt数');ax.set_xticks(range(5));ax.set_xlim(0,4.2);ax.invert_yaxis();ax.spines['left'].set_visible(False)
finish(fig,'05-sample-boundaries','R1/R2原件、失败门禁及费用全部保留；不择优剔除、不合并不同M策略。全批192/192结算、unknown0，估算峰价$0.52869。')

print(json.dumps(dict(figures=5,new_model_requests=0,output=str(OUT))))
