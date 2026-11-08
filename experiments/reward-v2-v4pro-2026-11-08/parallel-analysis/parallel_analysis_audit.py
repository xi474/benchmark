import json, pathlib, collections, hashlib, csv, re, datetime, argparse

parser=argparse.ArgumentParser(description='Offline parallel trigger evidence audit; no model/network requests.')
parser.add_argument('--outputs-root',type=pathlib.Path,required=True)
parser.add_argument('--release-root',type=pathlib.Path,required=True)
parser.add_argument('--output-dir',type=pathlib.Path,required=True)
args=parser.parse_args()
OUT,RELEASE,DEST=args.outputs_root,args.release_root,args.output_dir
DEST.mkdir(exist_ok=True,parents=True)
cells = json.loads((RELEASE/'results.json').read_text())['baseline_cells']
by_stage = collections.defaultdict(list)
for c in cells:
    p = (OUT/c['result_locator']).parent
    stage = next((a for a in [p,*p.parents] if (a/'gateway-requests.jsonl').exists()), None)
    if stage: by_stage[stage].append(c)
    elif c['arm']!='roma': raise ValueError(('NO_GATEWAY',c['arm'],c['task']))
rows=[]
for stage, selected in by_stage.items():
    ids={c['trial_id']:c for c in selected}
    obs=collections.defaultdict(list)
    source=stage/'gateway-requests.jsonl'
    for line in source.open(encoding='utf-8'):
        x=json.loads(line)
        if x.get('type')=='request-observation' and x.get('trial_id') in ids:
            obs[x['trial_id']].append(x)
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    for trial,c in ids.items():
        xx=obs[trial]; tools=collections.Counter(t.get('name') or t.get('type') for x in xx for t in x.get('tools',[]))
        row={k:c[k] for k in ['arm','task','dataset','trial_id','classification','result_locator']}
        schemas=collections.defaultdict(set)
        for x in xx:
            for t in x.get('tools',[]):schemas[t.get('name') or t.get('type')].add(t.get('schema_sha256'))
        row.update(observations=len(xx),tools=sorted(tools),tool_request_counts=dict(tools),tool_schema_hashes={k:sorted(v) for k,v in schemas.items()},tool_status=dict(collections.Counter(x.get('tools_status') for x in xx)),modes=dict(collections.Counter(str((x.get('thinking_type'),x.get('reasoning_effort'))) for x in xx)),gateway_source=str(source.relative_to(OUT)).replace('\\','/'),gateway_sha256=sha,first_request_sha256=xx[0]['request_sha256'] if xx else None)
        rows.append(row)
for c in cells:
    if c['arm']!='roma':continue
    f=(OUT/c['result_locator']).parent/'agent/telemetry/http-requests.json'
    requests=json.loads(f.read_text(encoding='utf-8'))['requests']
    row={k:c[k] for k in ['arm','task','dataset','trial_id','classification','result_locator']}
    row.update(observations=len(requests),tools=[],tool_request_counts={},tool_status={'native-DSPy-prompt-tool-protocol':len(requests)},modes=dict(collections.Counter(str(x.get('thinking_type')) for x in requests)),gateway_source=f.relative_to(OUT).as_posix(),gateway_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),first_request_sha256=next((x.get('request_sha256') for x in requests if x.get('request_sha256')),None),api_tool_count_distribution=dict(collections.Counter(str(x.get('request_shape',{}).get('tool_count')) for x in requests)),module_distribution=dict(collections.Counter(x.get('agent_definition_id') for x in requests)))
    rows.append(row)
assert len(rows)==392 and len({(r['arm'],r['task']) for r in rows})==392
result={'schema':'seven-harness-parallel-trigger-evidence/1','scope':'392 selected baseline attempts; independent repeats excluded','rows':rows}
(DEST/'request-tool-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
for arm in sorted(set(c['arm'] for c in cells)):
    rr=[r for r in rows if r['arm']==arm]
    print(arm, 'runs',len(rr),'obs',sum(r['observations'] for r in rr),'noobs',sum(not r['observations'] for r in rr))
    union=sorted(set(t for r in rr for t in r['tools']))
    print('TOOLS',union)
    print('EXPOSURE',{t:sum(t in r['tools'] for r in rr) for t in union if any(s in t.lower() for s in ['spawn','task','agent','delegate','team','plan'])})
    print('STATUSES',dict(sum((collections.Counter(r['tool_status']) for r in rr),collections.Counter())))

native=[]
old=json.loads((RELEASE/'runtime-multiagent-audit.json').read_text(encoding='utf-8'))
la={r['task']:r for r in old['latte']}
for c in cells:
    p=(OUT/c['result_locator']).parent/'agent'
    row={k:c[k] for k in ['arm','task','dataset','classification','result_locator']}
    calls=collections.Counter(); plans=[]; planning_ends=[]; dispatches=[]; caps=[]; planning_replies=[]
    if c['arm']=='latte-planning-adapted': f=p/'latte-run/events.jsonl'
    elif c['arm']=='codex': f=p/'monitoring/native-telemetry/events-v2.jsonl'
    else: f=p/'telemetry/events-v2.jsonl'
    if f.exists():
        row.update(events_source=f.relative_to(OUT).as_posix(),events_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
        for line in f.open(encoding='utf-8'):
            x=json.loads(line);typ=x.get('event_type') or x.get('type'); pl=x.get('payload',{})
            if typ in ['tool.started','tool.reported']: calls[x.get('tool_name') or pl.get('tool_name') or pl.get('tool') or 'unknown']+=1
            if typ=='plan.created' and c['arm']=='langgraph':
                tasks=pl.get('tasks') or []; deps={t['id']:set(t.get('depends_on') or []) for t in tasks};waves=[]
                while deps:
                    ready=sorted(k for k,v in deps.items() if not v)
                    if not ready:break
                    waves.append(ready)
                    for k in ready:deps.pop(k)
                    for v in deps.values():v.difference_update(ready)
                plans.append({'tasks':[{k:t.get(k) for k in ['id','depends_on','write_scope','parallel_group']} for t in tasks],'waves':waves,'max_wave_width':max(map(len,waves),default=0)})
            if typ=='planning_phase_end': planning_ends.append({k:x.get(k) for k in ['tasks_discovered','turns','max_turns','round']})
            if typ=='planning_reply':
                txt=x.get('text','');planning_replies.append({'turn':x.get('turn'),'stored_chars':len(txt),'stored_text_is_prefix':len(txt)==4000,'action_open_tags':dict(collections.Counter(re.findall(r'<([a-z_]+)(?:\s|/?>)',txt)))})
            if typ=='round_dispatch':dispatches.append({k:v for k,v in x.items() if k not in ['ts','type']})
            if typ=='telemetry.capability':
                for k in ['nanobot_snapshot_version','nanobot_version','condition','subagent_capability_available']:
                    if k in pl:caps.append({k:pl[k]})
        row.update(tool_calls=dict(calls),plans=plans,planning_ends=planning_ends,planning_reply_metadata=planning_replies,capabilities=caps)
        if dispatches:row['dispatches']=dispatches
    if c['arm']=='latte-planning-adapted':row['latte_recomputed']=la[c['task']]
    if c['arm']=='roma':
        f=p/'telemetry/roma-structure.json';x=json.loads(f.read_text(encoding='utf-8'));row['roma_metrics']=x['metrics'];row['roma_structure_source']=f.relative_to(OUT).as_posix();row['roma_structure_sha256']=hashlib.sha256(f.read_bytes()).hexdigest()
        row['roma_plan_metadata']=[{'task_node_id':plan.get('task_node_id'),'module_invocation_id':plan.get('module_invocation_id'),'source':plan.get('source'),'scope':plan.get('scope'),'subtasks':[{'index':i,'task_type':t.get('task_type'),'dependencies':t.get('dependencies')} for i,t in enumerate(plan.get('raw',{}).get('subtasks') or [])]} for plan in x['plans']]
    native.append(row)
(DEST/'native-trigger-evidence.json').write_text(json.dumps({'rows':native},ensure_ascii=False,indent=2),encoding='utf-8')
for arm in sorted(set(c['arm'] for c in cells)):
    rr=[r for r in native if r['arm']==arm];calls=sum((collections.Counter(r.get('tool_calls',{})) for r in rr),collections.Counter())
    print('NATIVE',arm,'tools',dict(calls),'versions',str([r['capabilities'] for r in rr[:1]]))
    if arm=='langgraph':print('WAVE_WIDTHS',dict(collections.Counter(p['max_wave_width'] for r in rr for p in r['plans'])))
    if arm=='latte-planning-adapted':print('NO_TEAMMATE',[(r['task'],r['planning_ends'],r['latte_recomputed']['teammate_turn_width']) for r in rr if not r['latte_recomputed']['responding_teammates']])
    if arm=='roma':print('SERIAL_LEAVES',[(r['task'],r['classification'],r['roma_metrics']) for r in rr if r['roma_metrics']['leaf_executor_parallel_width']<=1])

positive=next(c for c in cells if c['arm']=='codex' and c['task']=='original/linux_release_analysis')
pp=(OUT/positive['result_locator']).parent/'agent'
ctx=json.loads((pp/'monitoring/native-codex-observation.json').read_text(encoding='utf-8'))['extra']['native_codex']
root_id=ctx['root_thread_id']; timelines=[];root_calls=[]
for f in sorted((pp/'sessions').rglob('*.jsonl')):
    es=[json.loads(l) for l in f.open(encoding='utf-8')]
    if root_id in f.name:
        root_calls=[{'timestamp':e.get('timestamp'),'tool':e.get('payload',{}).get('name'),'task_name':json.loads(e['payload'].get('arguments') or '{}').get('task_name')} for e in es if e.get('payload',{}).get('type')=='function_call' and e['payload'].get('name')=='spawn_agent']
        continue
    starts=[e['timestamp'] for e in es if e.get('payload',{}).get('type')=='task_started'];ends=[e['timestamp'] for e in es if e.get('payload',{}).get('type')=='task_complete']
    timelines.append({'source':f.relative_to(OUT).as_posix(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'own_task_start':starts[-1] if starts else None,'own_task_end':ends[-1] if ends else None,'inherited_history_excluded':True})
def epoch(t):return datetime.datetime.fromisoformat(t.replace('Z','+00:00')).timestamp()
timeline_points=sorted([(epoch(r['own_task_start']),1) for r in timelines]+[(epoch(r['own_task_end']),-1) for r in timelines]);width=active=0
for _,delta in timeline_points:active+=delta;width=max(width,active)
timeline={'task':positive['task'],'root_thread_id':root_id,'root_spawn_calls':root_calls,'children':timelines,'child_lifecycle_parallel_width':width,'all_three_overlap_seconds':min(epoch(r['own_task_end']) for r in timelines)-max(epoch(r['own_task_start']) for r in timelines),'tool_parallel_execution':None,'boundary_note':'native task lifecycle includes wait, not exact model HTTP or tool execution span'}
(DEST/'codex-positive-timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
print('CODEX_TIMELINE',width,timeline['all_three_overlap_seconds'])

requests_by_key={(r['arm'],r['task']):r for r in rows}
lang_width={r['task']:r['worker_width'] for r in old['langgraph']}
csv_rows=[]
for r in native:
    q=requests_by_key[r['arm'],r['task']]
    row={k:r[k] for k in ['arm','task','dataset','classification','result_locator','events_source','events_sha256']}
    row.update(actual_api_tools='|'.join(q['tools']),request_source=q['gateway_source'],request_source_sha256=q['gateway_sha256'],delegation_tool_calls=sum(r['tool_calls'].get(t,0) for t in ['spawn','task','spawn_agent','spawn_teammate']),planning_seed_tasks=None,plan_max_wave_width=None,observed_parallel_width=None,parallel_scope=None,tool_parallel_width=None)
    if r['arm']=='langgraph':row.update(plan_max_wave_width=r['plans'][0]['max_wave_width'],observed_parallel_width=lang_width[r['task']],parallel_scope='worker-lifecycle')
    elif r['arm']=='latte-planning-adapted':row.update(planning_seed_tasks=r['planning_ends'][0]['tasks_discovered'],observed_parallel_width=r['latte_recomputed']['teammate_turn_width'],parallel_scope='teammate-model-reply-turn',tool_parallel_width=r['latte_recomputed']['teammate_tool_width'])
    elif r['arm']=='roma':row.update(observed_parallel_width=r['roma_metrics']['leaf_executor_parallel_width'],parallel_scope='leaf-executor-module-activity',tool_parallel_width=r['roma_metrics']['tool_parallel_width'])
    elif r['arm']=='codex':row.update(observed_parallel_width=3 if r['task']==positive['task'] else 0,parallel_scope='native-child-task-lifecycle')
    else:row.update(observed_parallel_width=0,parallel_scope='no-child-agent-observed')
    csv_rows.append(row)
with (DEST/'parallel-trigger-cells-392.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(csv_rows[0]));w.writeheader();w.writerows(csv_rows)
zero=[r for r in native if r['arm']=='latte-planning-adapted' and not r['latte_recomputed']['responding_teammates']]
assert len(zero)==17 and all(r['planning_ends'][0]['tasks_discovered']==0 and r['planning_ends'][0]['turns']==5 for r in zero)
assert sum(len(r['planning_reply_metadata']) for r in zero)==85
assert all(not x['stored_text_is_prefix'] and not x['action_open_tags'].get('discover_task') for r in zero for x in r['planning_reply_metadata'])
assert all(r['plans'][0]['max_wave_width']==lang_width[r['task']] for r in native if r['arm']=='langgraph')
assert len(root_calls)==3 and width==3
for arm,tool in [('nanobot','spawn'),('opencode','task'),('dsh','spawn_teammate'),('codex','collaboration')]:
    assert sum(r['arm']==arm and tool in r['tools'] for r in rows)==56
assert sum(r['tool_calls'].get('spawn',0) for r in native if r['arm']=='nanobot')==0
assert sum(r['tool_calls'].get('task',0) for r in native if r['arm']=='opencode')==0
assert sum(r['tool_calls'].get('spawn_teammate',0) for r in native if r['arm']=='dsh')==0
checks={'cells':392,'unique_cells':392,'langgraph_plan_vs_worker_width_matches':56,'latte_zero_seed_cases':17,'latte_zero_seed_full_planning_replies':85,'optional_delegation_tool_exposed_trials_per_harness':56,'codex_root_spawn_calls':3,'codex_child_lifecycle_parallel_width':3,'provider_requests_in_this_audit':0,'source_results_sha256':hashlib.sha256((RELEASE/'results.json').read_bytes()).hexdigest(),'previous_runtime_audit_sha256':hashlib.sha256((RELEASE/'runtime-multiagent-audit.json').read_bytes()).hexdigest(),'validation':'passed'}
(DEST/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print('CHECKS',json.dumps(checks))
