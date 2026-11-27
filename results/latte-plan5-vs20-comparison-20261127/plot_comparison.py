"""Reproducible local PNG/SVG figures; no models or network."""
from pathlib import Path
import json
import os

HERE=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(HERE/'.matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

font=Path(os.environ.get('LATTE_CHINESE_FONT', 'C:/Windows/Fonts/msyh.ttc'))
if not font.is_file():
    raise SystemExit('Set LATTE_CHINESE_FONT to an installed Chinese font, e.g. NotoSansCJK-Regular.ttc')
font_manager.fontManager.addfont(str(font))
plt.rcParams.update({'font.family':font_manager.FontProperties(fname=str(font)).get_name(),
    'axes.unicode_minus':False,'svg.fonttype':'none','font.size':10,
    'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#c5cbd1',
    'axes.labelcolor':'#27323c','text.color':'#17232e','xtick.color':'#344352','ytick.color':'#344352'})
D=json.loads((HERE/'comparison.json').read_text(encoding='utf-8'))
S={(x['provider'],x['planning_limit']):x for x in D['summaries']}
providers=['deepseek','qwen'];labels=['DeepSeek V4 Pro 普通','Qwen3.8-Max 关闭推理']
colors=['#a9b2ba','#187e94']

def grouped(ax,field,title,ylabel,formatter=None,ymax=None):
    x=np.arange(2);width=.34
    for j,n in enumerate([5,20]):
        values=[float(S[p,n][field]) for p in providers]
        bars=ax.bar(x+(j-.5)*width,values,width,color=colors[j],label=f'{n}轮')
        text=[formatter(S[p,n]) if formatter else f'{v:.2f}' for p,v in zip(providers,values)]
        ax.bar_label(bars,labels=text,padding=4,fontsize=9)
    ax.set_title(title,loc='left',fontweight='bold',fontsize=12,pad=14)
    ax.set_xticks(x,labels,fontsize=9);ax.set_ylabel(ylabel);ax.set_xlabel('模型（每条件59题）')
    ax.set_axisbelow(True);ax.grid(axis='y',color='#e7ebee',lw=.65)
    ax.set_ylim(0,ymax or max(float(S[p,n][field]) for p in providers for n in [5,20])*1.32)

fig,axes=plt.subplots(2,3,figsize=(16,11))
grouped(axes[0,0],'strict_percent','严格通过率','通过题数 / 59（%）',lambda r:f"{r['strict_passed']}/59\n{r['strict_percent']:.2f}%",100)
grouped(axes[0,1],'api_percent','核心 API 检查通过率','通过检查 / 803（%）',lambda r:f"{r['api_passed']}/803\n{r['api_percent']:.2f}%",100)
for r in D['summaries']:r['reward_percent']=100*float(r['reward'])/138
grouped(axes[0,2],'reward_percent','新版 reward（严格50%＋登记检查50%）','reward / 138（%）',lambda r:f"{float(r['reward']):.3f}\n{r['reward_percent']:.2f}%",100)
grouped(axes[1,0],'mean_e2e_seconds','平均完整 E2E','秒 / 题',lambda r:f"{r['mean_e2e_seconds']:.1f}s")
for r in D['summaries']:r['tokens_m']=r['total_tokens']/1e6
grouped(axes[1,1],'tokens_m','总 tokens（输入＋输出）','百万 tokens / 59题',lambda r:f"{r['tokens_m']:.2f}M")
ax=axes[1,2];x=np.arange(2);width=.34
for j,n in enumerate([5,20]):
    vals=[1 if n==5 else S[p,20]['cost_comparison']/S[p,5]['cost_comparison'] for p in providers]
    bars=ax.bar(x+(j-.5)*width,vals,width,color=colors[j],label=f'{n}轮')
    ax.bar_label(bars,labels=[f'{v:.2f}×' for v in vals],padding=4,fontsize=10)
ax.axhline(1,color='#78828b',lw=.8,ls='--');ax.set_ylim(0,11.5)
ax.set_xticks(x,labels,fontsize=9);ax.set_xlabel('模型（两条件采用相同的各自费率）');ax.set_ylabel('费用倍率（5轮＝1）')
ax.set_title('费用倍率（估算，非账单）',loc='left',fontweight='bold',fontsize=12,pad=14)
ax.set_axisbelow(True);ax.grid(axis='y',color='#e7ebee',lw=.65)
ax.text(.03,.96,f"DeepSeek：USD {S['deepseek',5]['cost_comparison']:.2f} → {S['deepseek',20]['cost_comparison']:.2f}\nQwen：CNY {S['qwen',5]['cost_comparison']:.2f} → {S['qwen',20]['cost_comparison']:.2f}",transform=ax.transAxes,va='top',fontsize=9)
fig.suptitle('LATTE 规划5轮 vs 20轮：收益与代价',fontsize=21,fontweight='bold',y=.98)
fig.text(.5,.935,'同一59题 × 两模型；各条件每题一次，历史配对而非严格因果实验',ha='center',fontsize=12)
handles,legend=axes[0,0].get_legend_handles_labels();fig.legend(handles,legend,loc='upper center',bbox_to_anchor=(.5,.91),ncol=2,frameon=False)
fig.subplots_adjust(top=.83,bottom=.14,hspace=.48,wspace=.32)
fig.text(.055,.075,'口径：API为803项核心检查的微平均；reward满分138。完整E2E包含空规划早退，不能把早退当作更快完成。',fontsize=10)
fig.text(.055,.048,'费用：DeepSeek两组统一冻结峰价重计；Qwen统一目录价，无缓存折扣。不同币种仅比较各自倍率，均非实际账单。',fontsize=10)
fig.text(.055,.021,'来源：冻结Harbor评分、原生规划事件与网关usage，5轮历史选择／20轮2026-11-26至27；DeepSeek历史复用及入口差异见交互报告。',fontsize=9,color='#5d6871')
for ext in ['png','svg']:fig.savefig(HERE/f'overview.{ext}',dpi=190,facecolor='white')
plt.close(fig)

fig=plt.figure(figsize=(14,10));grid=fig.add_gridspec(2,2,height_ratios=[1,1.12],hspace=.5,wspace=.55)
ax=fig.add_subplot(grid[0,:]);y=np.arange(4)
conditions=[('deepseek',5),('deepseek',20),('qwen',5),('qwen',20)]
left=np.zeros(4);palette=['#d7dde2','#d1ae72','#187e94'];flow_names=['未生成任务图','有图但未严格通过','严格通过']
for category,color in zip(flow_names,palette):
    values=np.array([S[k]['flow_counts'].get(category,0) for k in conditions])
    ax.barh(y,values,left=left,color=color,height=.58,label=category)
    for i,v in enumerate(values):
        if v:ax.text(left[i]+v/2,i,str(v),ha='center',va='center',fontsize=12,color='white' if category=='严格通过' else '#25323d',fontweight='bold')
    left+=values
ax.set_yticks(y,['DeepSeek · 5轮','DeepSeek · 20轮','Qwen · 5轮','Qwen · 20轮']);ax.invert_yaxis();ax.set_xlim(0,59)
ax.set_xlabel('题数（每行固定59题）');ax.set_title('空图减少后，新增任务是否最终严格通过？',loc='left',fontsize=14,fontweight='bold',pad=18)
ax.legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,-.22),frameon=False)
for i,p in enumerate(providers):
    ax=fig.add_subplot(grid[1,i]);tr=next(t for t in D['transitions'] if t['provider']==p)['graph']
    matrix=np.array([[tr.get('无图→无图',0),tr.get('无图→有图',0)],[tr.get('有图→无图',0),tr.get('有图→有图',0)]])
    ax.imshow(matrix,cmap='Blues',vmin=0,vmax=59)
    for row in range(2):
        for col in range(2):ax.text(col,row,str(matrix[row,col]),ha='center',va='center',fontsize=24,fontweight='bold',color='#132433')
    ax.set_xticks([0,1],['20轮：无图','20轮：有图']);ax.set_yticks([0,1],['5轮：无图','5轮：有图']);ax.set_xlabel('20轮的规划结果');ax.set_ylabel('5轮的规划结果')
    ax.set_title(labels[i]+' · 同题建图迁移',fontsize=12,pad=14)
fig.suptitle('增加轮数有帮助，但并非每道题单调改善',fontsize=20,fontweight='bold',y=.98)
fig.text(.5,.028,'DeepSeek：原先通过的4题此次均未通过，新增另4题通过；Qwen：原先有图的3题此次全部空图，另26题新生成图。',ha='center',fontsize=10)
fig.text(.5,.008,'来源：59题逐题配对；每条件单次，模型随机性、历史版本及运行条件未完全控制。',ha='center',fontsize=9,color='#5d6871')
fig.subplots_adjust(top=.90,bottom=.12)
for ext in ['png','svg']:fig.savefig(HERE/f'flow-and-transitions.{ext}',dpi=190,facecolor='white')
plt.close(fig)

tasks=sorted({r['task_id'] for r in D['rows']});lookup={(r['provider'],r['planning_limit'],r['task_id']):r for r in D['rows']}
matrix=np.array([[lookup[p,n,t]['api_percent'] for t in tasks] for p,n in conditions])
fig,ax=plt.subplots(figsize=(18,4.7));image=ax.imshow(matrix,aspect='auto',cmap='Blues',vmin=0,vmax=100)
ax.set_yticks(range(4),['DeepSeek · 5轮','DeepSeek · 20轮','Qwen · 5轮','Qwen · 20轮']);ax.set_xticks(range(59),tasks,rotation=90,fontsize=8)
ax.set_xlabel('任务ID（同一列为同一道题）');ax.set_ylabel('模型 × 规划轮数');ax.set_title('逐题核心 API 通过率：颜色越深，通过比例越高',loc='left',fontsize=16,pad=18)
cb=fig.colorbar(image,ax=ax,fraction=.018,pad=.015);cb.set_label('核心 API 检查通过率（%）')
for i in range(1,len(tasks)):
    if tasks[i].rstrip('0123456789')!=tasks[i-1].rstrip('0123456789'):ax.axvline(i-.5,color='#65717b',lw=.8)
fig.subplots_adjust(left=.12,right=.94,top=.82,bottom=.30)
fig.text(.12,.06,'来源：236份已核验评分；全图使用同一0–100%色标。API率与严格整题通过不同，逐题准确分子／分母见交互明细。',fontsize=10,color='#5d6871')
for ext in ['png','svg']:fig.savefig(HERE/f'task-api-heatmap.{ext}',dpi=200,facecolor='white')
plt.close(fig)
print(json.dumps({'plots':3,'formats':['png','svg'],'provider_requests':0}))
