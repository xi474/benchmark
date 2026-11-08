"""Derive API-visible input-prefix cache rates from published, deduplicated usage."""
import argparse, collections, csv, hashlib, json, pathlib, statistics

DATASETS={'original14':14,'mixed16-v4':16,'medium26':26}
PREFIX={'original':'original14','hard':'mixed16-v4','medium':'medium26'}
ARMS=['nanobot','opencode','codex','dsh','langgraph','latte-planning-adapted','roma','aorchestra']

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):
    eol='\r\n' if p.exists() and b'\r\n' in p.read_bytes() else '\n'
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline=eol)
def csv_save(p,rows):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def classify(input_known,hit_known,cache_complete,sent,settled,unknown,inflight=0):
    for value in [input_known,hit_known,sent,settled,unknown,inflight]:
        if value is not None and (type(value) is not int or value<0):raise ValueError('Invalid usage counter')
    if input_known is not None and hit_known is not None and hit_known>input_known:raise ValueError('Cache hit exceeds input')
    if input_known is None or hit_known is None or cache_complete is not True:
        return None,None,'unavailable_cache_or_input'
    known=hit_known/input_known if input_known else None
    if None in [sent,settled,unknown,inflight]:return None,known,'unknown_request_coverage'
    if unknown or inflight or sent!=settled:return None,known,'partial_unknown_request'
    if input_known==0:return None,None,'not_applicable_zero_input'
    return known,known,'observed'

def normalize(r,source,source_hash,aorchestra=False,cohort='baseline'):
    if aorchestra:
        arm='aorchestra';ds=PREFIX[r['task'].split('/')[0]]
        inp=r.get('known_settled_usage',{}).get('input_tokens');hit=r.get('cache_tokens')
        sent,settled,unknown,inflight=(r.get(k) for k in ['request_count','settled_count','unknown_count','inflight_count'])
        cache_complete=hit is not None
        classification=r['quality_status']+';orchestration='+r['orchestration_status']
        usage_status=r['usage_status'];trial=r['trial'];loc=r['evidence_root']
        cache_evidence='nonnull source aggregate; missing cache would remain null'
    else:
        arm=r['arm'];ds=r['dataset'];inp=r.get('tokens_input_known');hit=r.get('tokens_cache_hit_known')
        sent,settled,unknown=(r.get(k) for k in ['model_requests_sent','model_requests_settled','model_requests_unknown'])
        inflight=0 if None not in [sent,settled,unknown] and sent-settled==unknown else None
        cache_complete=r.get('cache_usage_complete');classification=r['classification'];usage_status=r['tokens_status']
        trial=r['trial_id'];loc=r['result_locator'];cache_evidence='cache_usage_complete from deduplicated settled requests'
    full,known,status=classify(inp,hit,cache_complete,sent,settled,unknown,inflight)
    return dict(cohort=cohort,arm=arm,dataset=ds,task=r['task'],trial_id=trial,classification=classification,
                input_tokens_known=inp,cache_hit_tokens_known=hit,cache_miss_tokens_known=inp-hit if inp is not None and hit is not None else None,
                input_cache_hit_rate=full,observed_input_cache_hit_rate=known,cache_rate_status=status,
                cache_usage_complete=cache_complete,cache_coverage_evidence=cache_evidence,
                requests_sent=sent,requests_settled=settled,requests_unknown=unknown,requests_inflight=inflight,
                request_coverage_evidence='source request/settled/unknown/inflight counters' if aorchestra else 'selected terminal attempt; inflight inferred from sent-settled==unknown, not a live provider query',
                source_usage_status=usage_status,source_file=source,source_sha256=source_hash,evidence_locator=loc)

def summarize(rows,arm,dataset):
    valid=[r for r in rows if r['cache_rate_status']=='observed']
    inp=sum(r['input_tokens_known'] or 0 for r in rows);hit=sum(r['cache_hit_tokens_known'] or 0 for r in rows)
    unknown=sum(r['requests_unknown'] or 0 for r in rows)
    coverage=all(r['cache_rate_status'] in ['observed','not_applicable_zero_input'] for r in rows)
    cache_complete=all(r['cache_usage_complete'] is True for r in rows)
    known=hit/inp if inp and cache_complete else None
    status='observed' if coverage and inp else 'not_applicable_zero_input' if coverage else 'partial_unknown_request' if any(r['cache_rate_status']=='partial_unknown_request' for r in rows) else 'unavailable_cache_or_input'
    return dict(arm=arm,dataset=dataset,cells=len(rows),cache_measured_cells=len(valid),cache_partial_cells=sum(r['cache_rate_status']=='partial_unknown_request' for r in rows),cache_missing_cells=sum(r['cache_rate_status'] not in ['observed','partial_unknown_request','not_applicable_zero_input'] for r in rows),
                input_tokens_known=inp,cache_hit_tokens_known=hit,cache_miss_tokens_known=inp-hit,
                input_cache_hit_rate=known if coverage else None,observed_input_cache_hit_rate=known,
                input_cache_hit_rate_macro=statistics.mean(r['input_cache_hit_rate'] for r in valid) if valid else None,
                cache_rate_status=status,requests_unknown=unknown)

def generate(root):
    sf=root/'seven-harnesses/results.json';af=root/'aorchestra/results-56.json';s=read(sf);a=read(af)
    rows=[normalize(r,'seven-harnesses/results.json',digest(sf)) for r in s['baseline_cells']]
    rows += [normalize(r,'aorchestra/results-56.json',digest(af),True) for r in a['rows']]
    repeats=[normalize(r,'seven-harnesses/results.json',digest(sf),cohort='independent-repeat') for r in s['latte_independent_repeats']]
    assert len(rows)==448 and len({(r['arm'],r['task']) for r in rows})==448 and len(repeats)==4
    groups=[summarize([r for r in rows if r['arm']==arm and r['dataset']==ds],arm,ds) for arm in ARMS for ds in DATASETS]
    arms=[summarize([r for r in rows if r['arm']==arm],arm,'all56') for arm in ARMS]
    d=root/'cache-analysis';d.mkdir(exist_ok=True)
    csv_save(d/'cells-448.csv',rows);csv_save(d/'latte-independent-repeats-4.csv',repeats);csv_save(d/'harness-summary-8.csv',arms)
    metadata=dict(schema='api-input-context-cache-rates/1',metric='API-visible input-prefix/context cache token hit ratio',unit='fraction, 0..1',
                  formula='sum(cache-hit input tokens) / sum(input tokens); output excluded',strict_rate_policy='null when actual request usage coverage is incomplete; known settled component reported separately',
                  cohorts='448 selected baseline/comparison cells; 4 LATTE independent repeats excluded from baseline',source_sha256={'seven-harnesses/results.json':digest(sf),'aorchestra/results-56.json':digest(af)},
                  engine_internal_k_cache_hit_rate=None,engine_internal_v_cache_hit_rate=None,provider_requests=0,
                  rows=rows,independent_repeats=repeats,harness_summary=arms,dataset_summary=groups)
    save(d/'results.json',metadata)
    for ds in DATASETS:
        tasks=sorted({r['task'] for r in rows if r['dataset']==ds});matrix=[];states=[]
        for task in tasks:
            rr={r['arm']:r for r in rows if r['task']==task};assert set(rr)==set(ARMS)
            matrix.append({'task':task,**{arm:rr[arm]['input_cache_hit_rate'] for arm in ARMS}})
            states.append({'task':task,**{arm:rr[arm]['cache_rate_status'] for arm in ARMS}})
        csv_save(d/('matrix-'+ds+'.csv'),matrix);csv_save(d/('matrix-coverage-'+ds+'.csv'),states)
    old=read(root/'harness-dataset-summary-24.json')
    for x in old:
        g=next(g for g in groups if (g['arm'],g['dataset'])==(x['arm'],x['dataset']))
        for k in ['input_cache_hit_rate','observed_input_cache_hit_rate','input_cache_hit_rate_macro','cache_rate_status','cache_measured_cells','cache_partial_cells','cache_missing_cells']:x[k]=g[k]
    save(root/'harness-dataset-summary-24.json',old);csv_save(root/'harness-dataset-summary-24.csv',old)
    report=['# 逐任务×Harness输入上下文缓存命中率','',
            '本报告是2026-11-08已发布运行结果的离线补充，新增供应商请求0。范围为八臂各56题，共448个选定题位；LATTE四个独立补跑另列，不覆盖原基线。',
            '', '## 指标定义与覆盖率','',
            '**输入缓存命中率 = 缓存命中输入token数 / 输入token数。** 每题跨已结算请求先加总再相除；跨题微平均同样按token加权，宏平均只取有完整覆盖的题目比例。输出tokens不进分母，cache-hit是input的子集，不能再与input相加。',
            '', '来源是DeepSeek API返回usage中的prompt_cache_hit_tokens或Responses input_tokens_details.cached_tokens，经原网关去重归一为cache_tokens。参考[官方上下文缓存说明](https://api-docs.deepseek.com/zh-cn/guides/kv_cache/)、[Responses usage说明](https://api-docs.deepseek.com/guides/responses_api/)。这不是GPU内部每层K/V缓存的访问命中率，也不提供KV显存或驱逐次数。',
            '', '447/448个基线题位可给出完整请求覆盖的比例。ROMA original/release_compatibility_program有193次实际发送、192次结算、1次未知，完整比例保持null；只给出已结算部分比例。下表带†的是已知部分，不能称完整比例。CSV数值矩阵的该格留空，覆盖矩阵明确标记partial_unknown_request。缺失不记0；真实返回cache-hit=0且输入>0才是0%。',
            '', '缓存指标独立于任务质量：invalid_submission、预算跳过或Agent异常仍可有真实已结算usage，继续保留分类，不把它们称为任务成功。AOrchestra两题native summary缺测沿用provider-egress来源，未伪造native总量。',
            '', '## 八臂56题汇总','',
            '| Harness | 输入tokens（已知） | 命中tokens（已知） | token加权命中率 | 完整覆盖题数 |',
            '|---|---:|---:|---:|---:|']
    def display(r):
        v=r['input_cache_hit_rate'];known=r['observed_input_cache_hit_rate']
        return f'{v:.2%}' if v is not None else f'{known:.2%}†' if known is not None else '未知/不适用'
    for g in arms:report.append(f"| {g['arm']} | {g['input_tokens_known']:,} | {g['cache_hit_tokens_known']:,} | {display(g)} | {g['cache_measured_cells']}/{g['cells']} |")
    report += ['', '比例差异描述的是本批请求的上下文前缀复用，不足以单独归因为Harness架构优劣；不保证输出质量或实际推理加速。','', '## 逐题矩阵','', '表格显示百分比；CSV数值为0至1的小数。所有原14、mixed16-v4、Medium26任务均覆盖，不仅是有API评分分母的任务。']
    for ds in DATASETS:
        report += ['', '### '+ds,'', f'[数值矩阵](matrix-{ds}.csv) · [覆盖状态矩阵](matrix-coverage-{ds}.csv)','', '| 任务 | '+' | '.join(ARMS)+' |','|---|'+'---:|'*len(ARMS)]
        for task in sorted({r['task'] for r in rows if r['dataset']==ds}):
            rr={r['arm']:r for r in rows if r['task']==task};report.append('| '+task+' | '+' | '.join(display(rr[arm]) for arm in ARMS)+' |')
    report += ['', '## LATTE四个独立补跑','', '| 任务 | 原终态分类 | 输入tokens | 命中tokens | 命中率 |','|---|---|---:|---:|---:|']
    for r in repeats:report.append(f"| {r['task']} | {r['classification']} | {r['input_tokens_known']:,} | {r['cache_hit_tokens_known']:,} | {display(r)} |")
    report += ['', '## 文件与复核','',
               '- [448行长表](cells-448.csv)：每题的输入、命中/未命中tokens、完整比例、已知部分比例、请求结算状态、原终态分类与来源hash。',
               '- [结构化JSON](results.json)：448题、4补跑、8臂汇总及24组数据集汇总。',
               '- [八臂汇总CSV](harness-summary-8.csv)、[独立补跑CSV](latte-independent-repeats-4.csv)。',
               '- [生成脚本](../scripts/aggregate_input_cache_rates.py)与[独立校验器](../scripts/validate_input_cache_rates.py)，均无需模型或凭据。原七臂和AOrchestra来源JSON字节不变。',
               '', '生成：python scripts/aggregate_input_cache_rates.py；验证：python scripts/validate_publication.py。缺测状态、纯native/frozen/adapted标签及所有原reward/API/时间/费用口径保持。','']
    (d/'README.md').write_text('\n'.join(report),encoding='utf-8',newline='\n')
    index=root/'README.md';eol='\r\n' if b'\r\n' in index.read_bytes() else '\n';text=index.read_text(encoding='utf-8')
    marker='<!-- INPUT-CACHE-SUPPLEMENT -->'
    end_marker='<!-- /INPUT-CACHE-SUPPLEMENT -->'
    block=marker+'\n\n## 输入缓存命中率补充\n\n[查看56任务×八套Harness完整矩阵与口径](cache-analysis/README.md) · [448行逐题明细](cache-analysis/cells-448.csv) · [八臂汇总](cache-analysis/harness-summary-8.csv)。原14/mixed16-v4/Medium26均已统计，LATTE四个补跑单列。447格完整；ROMA一格因未知请求只报告已结算部分，完整比例留空。总汇总CSV/JSON已追加缓存比例与覆盖字段，原指标不变。\n'+end_marker+'\n'
    if marker in text:
        if end_marker not in text:raise ValueError('Missing supplement end marker; refuse to replace following content')
        begin=text.index(marker);end=text.index(end_marker,begin)+len(end_marker)
        text=text[:begin]+block.rstrip('\n')+text[end:]
    else:text+='\n'+block
    index.write_text(text,encoding='utf-8',newline=eol)
    print(json.dumps({'cache_cells':len(rows),'complete_rate_cells':sum(r['cache_rate_status']=='observed' for r in rows),'partial_cells':sum(r['cache_rate_status']=='partial_unknown_request' for r in rows),'independent_repeats':len(repeats),'provider_requests':0}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1]);args=parser.parse_args();generate(args.root)
