"""Emit one self-contained Canvas; no network or model access."""
import json
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
data = json.loads((here / 'canvas-data.json').read_text(encoding='utf-8'))
template = '''import { BarChart, Callout, Grid, H1, H2, Row, Select, Stack, Stat, Table, Text, TextInput, useCanvasState, useHostTheme } from "cursor/canvas";
const D = __DATA__;
const f=(n:number,d=1)=>n.toLocaleString("zh-CN",{minimumFractionDigits:d,maximumFractionDigits:d});
const pct=(n:number)=>f(n*100,2)+"%";
const label=(h:string)=>D.rows.find(r=>r.harness===h)!.harness_display;
export default function Qwen59Report(){
 const theme=useHostTheme();
 const [h,setH]=useCanvasState("qwen59-harness","");
 const [g,setG]=useCanvasState("qwen59-group","");
 const [task,setTask]=useCanvasState("qwen59-task","");
 const [metric,setMetric]=useCanvasState("qwen59-metric","quality");
 const [terminal,setTerminal]=useCanvasState("qwen59-terminal","");
 const selected=D.rows.filter(r=>(!h||r.harness===h)&&(!g||r.task_group===g)&&r.task_id.toLowerCase().includes(task.toLowerCase())&&(!terminal||(terminal==="strict"?r.strict_pass:r.terminal_classification!=="normal_agent_exit"||!r.integrity_ok)));
 const summary=D.summary.map(s=>[label(s.group),`${s.strict_passed}/59 · ${pct(s.strict_acc)}`,`${s.api_passed}/803 · ${pct(s.api_micro_acc)}`,`${f(Number(s.reward_sum),6)}/138`,f(s.mean_e2e_seconds),f(s.list_cost_cny,2)]);
 const quality=[{name:"严格 ACC（%）",data:D.summary.map(s=>s.strict_acc*100),tone:"neutral" as const},{name:"核心 API 微平均（%）",data:D.summary.map(s=>s.api_micro_acc*100),tone:"info" as const},{name:"reward /138（%）",data:D.summary.map(s=>s.reward_weighted_rate*100),tone:"warning" as const}];
 const perfKey=metric==="e2e"?"mean_e2e_seconds":metric==="tokens"?"total_tokens":"list_cost_cny";
 const perfName=metric==="e2e"?"完整 E2E 均值（秒/题）":metric==="tokens"?"输入＋输出合计（百万 tokens/59题）":"目录价比较额（人民币/59题，非账单）";
 return <main style={{padding:24,color:theme.text.primary,background:theme.bg.editor,maxWidth:1500,margin:"0 auto",lineHeight:1.6}}><Stack gap={18}>
 <H1>Qwen3.8-Max 关闭推理｜59题 × 6 Harness 最终汇总</H1>
 <Text>Upstream59 v2.1.0 · 2026-11-26 · LATTE planning-adapted。已授权基础设施补跑完成，按最新恢复版本选择354格；不取最高分，所有旧attempt保留。</Text>
 <Grid columns={4} gap={16}><Stat value="354 /354" label="评分、E2E、资源与已结算用量齐全"/><Stat value="134 /354" label="严格整题通过"/><Stat value="429.880109 /828" label="新版reward合计"/><Stat value="¥2,644.42" label="选定结果目录价，非账单"/></Grid>
 <Callout tone="warning" title="保留异常，避免误读"><Text>LATTE 56次五轮空规划、2次100轮未完成；较短耗时不是解题效率优势。另有15次累计2M token闸门、1次原生上下文超限；11格完整性失败与其他异常可重叠。历史总目录价¥2,746.41，另1笔旧429用量未知；实际Token Plan扣费未知。</Text></Callout>
 <H2>六套主表：质量、完整耗时与成本</H2>
 <Table headers={["Harness","严格ACC","核心API微平均","新版reward","平均完整E2E 秒","目录价CNY"]} rows={summary} striped/>
 <Text tone="secondary">每套固定59题、803个API检查、1217个登记核心检查，reward满分138。ACC=严格通过题数/59；API只含核心业务转换；reward=I×W×(0.5×登记检查通过率＋0.5×严格通过)。费用按冻结输入12/百万、输出36/百万CNY，不计缓存折扣。</Text>
 <Row gap={12}><Text weight="semibold">查看指标</Text><Select value={metric} onChange={setMetric} options={[{value:"quality",label:"ACC / API / reward"},{value:"e2e",label:"完整E2E"},{value:"tokens",label:"总tokens"},{value:"cost",label:"目录价成本"}]}/></Row>
 <H2>{metric==="quality"?"Harness × 质量百分比（%）":perfName}</H2>
 {metric==="quality"?<BarChart categories={D.summary.map(s=>label(s.group))} series={quality} height={320} yMax={100} valueSuffix="%" showValues/>:<BarChart categories={D.summary.map(s=>label(s.group))} series={[{name:perfName,data:D.summary.map(s=>s[perfKey]/(metric==="tokens"?1e6:1)),tone:"info"}]} height={300} showValues/>}
 <Text tone="secondary">横轴：Harness；纵轴：标题所示指标及单位。来源：354格原始score-v2、Harbor实际起止、gateway逐请求usage；2026-11-26。E2E包括初始化和评分。原批最多6Harbor/HTTP4，最后恢复单/双试次，存在资源条件差异。</Text>
 <H2>逐格结果：可筛选全部354格</H2>
 <Row gap={12} wrap><Select value={h} onChange={setH} options={[{value:"",label:"全部Harness"},...D.summary.map(s=>({value:s.group,label:label(s.group)}))]}/><Select value={g} onChange={setG} options={[{value:"",label:"全部任务组"},...['C20','MS10','MP25','N4'].map(s=>({value:s,label:s}))]}/><TextInput value={task} onChange={setTask} placeholder="按任务ID筛选，如C058"/><Select value={terminal} onChange={setTerminal} options={[{value:"",label:"全部终态"},{value:"strict",label:"严格通过"},{value:"anomaly",label:"非零退出或完整性失败"}]}/></Row>
 <Text tone="secondary">显示{selected.length}/354格。筛选只改变显示，不改变主表分母；缓存是输入子集，不重复相加。</Text>
 {selected.length>0&&<Table headers={["Harness /任务","严格","API","reward","E2E秒","输入tokens","输出tokens","缓存命中率","目录价CNY","终态"]} rows={selected.map(r=>[`${r.harness_display} /${r.task_id}`,r.strict_pass?"通过":r.integrity_ok?"未全过":"完整性失败",`${r.api_passed}/${r.api_total}`,`${f(Number(r.reward),6)}/${r.max_reward}`,f(r.e2e_seconds),f(r.input_tokens,0),f(r.output_tokens,0),pct(r.input_cache_hit_rate),f(r.list_cost_cny,3),r.terminal_classification])} stickyHeader striped style={{maxHeight:620}}/>}
 <Text tone="secondary">完整报告与CSV已落盘于项目outputs/qwen59-final-report-20261126-v1。所有354格reward已用workspace_reward.py复算、原评分及Harbor结果哈希已核对。旧MS02满分但429异常保留，新授权R3零分按规则选用；没有择优。此视图不发起网络或模型请求。</Text>
 </Stack></main>;
}
'''
target = Path(sys.argv[1])
target.write_text(template.replace('__DATA__', json.dumps(data,ensure_ascii=False,separators=(',',':'))), encoding='utf-8')
print(json.dumps({'canvas':str(target),'bytes':target.stat().st_size},ensure_ascii=False))
