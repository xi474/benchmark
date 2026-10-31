# 源码摘录（原文件只读）

行号按本次本地文件的物理行计；catalog 的 prompt 单独解码。

## S01

源文件：[snapshots/harness-v3-research/harbor-agents/harbor_agents/cli_agents.py](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/harness-v3-research/harbor-agents/harbor_agents/cli_agents.py)

SHA-256：`92cbde4e3f1faf7746df5b220fc4ae8abae3ccf2f52be5117e190d6d111eb618`

```text
25: CODEX_MULTI_AGENT_CONFIG: dict[str, Any] = {
26:     # Codex 0.164 defaults to the WebSocket Responses transport and attempts a
27:     # remote-compaction request over wss://. DeepSeek exposes the HTTP
28:     # Responses endpoint but not that WebSocket endpoint (405), so pin an
29:     # HTTP-only provider.
30:     "model_provider": "deepseek_http",
31:     "model_providers": {
32:         "deepseek_http": {
33:             "name": "DeepSeek HTTP",
34:             "base_url": "https://api.deepseek.com",
35:             "wire_api": "responses",
36:             "requires_openai_auth": True,
37:             "supports_websockets": False,
38:         }
39:     },
40:     "features": {
41:         "multi_agent_v2": {
42:             "enabled": True,
43:             # Soft, complexity-gated policy: delegate only when the task has
44:             # meaningful independent branches, not for small/linear tasks.
45:             "multi_agent_mode_hint_text": (
46:                 "Multi-agent delegation is available. Consider spawning a subagent "
47:                 "when the task has meaningful independent branches (for example "
48:                 "separate modules, sources, or verification tracks) and delegation "
49:                 "could save time or improve quality. Do not spawn subagents for "
50:                 "small or strictly linear tasks. When you delegate, give each "
51:                 "subagent a disjoint write scope and a concrete deliverable, "
52:                 "continue useful work yourself, and wait for required subagent "
53:                 "results before finalizing."
54:             ),
55:         }
```

```text
81: CODEX_CATALOG_FILE = (
82:     Path(__file__).resolve().parent.parent / "config" / "codex-model-catalog.json"
83: )
84: 
85: 
86: class CodexAgent(_HarborCodex):
87:     """Codex CLI + complexity-gated multi-agent config + optional C1 policy."""
88: 
89:     def __init__(self, *args: Any, **kwargs: Any) -> None:
90:         # Harbor loads the native config in Codex.__init__, so inject the
91:         # default before calling super(). An explicit caller config wins.
92:         config = dict(kwargs.get("config") or CODEX_MULTI_AGENT_CONFIG)
93:         # Codex's built-in catalog does not know DeepSeek. A local catalog is
94:         # required for freeform apply_patch/context metadata; without it Codex
95:         # falls back to generic metadata and drops its patch tool.
96:         config["model_catalog_json"] = CODEX_CATALOG_PATH
97:         kwargs["config"] = config
98:         super().__init__(*args, **kwargs)
99: 
100:     @override
101:     async def install(self, environment: BaseEnvironment) -> None:
102:         if CODEX_CATALOG_FILE.exists():
103:             encoded = base64.b64encode(CODEX_CATALOG_FILE.read_bytes()).decode("ascii")
104:             await self.exec_as_agent(
105:                 environment,
106:                 command=(
107:                     "set -eu; "
108:                     f"printf %s {encoded} | base64 -d > {CODEX_CATALOG_PATH}; "
109:                     f"test -s {CODEX_CATALOG_PATH}"
110:                 ),
111:             )
112:         probe = await environment.exec(
113:             command="command -v codex && codex --version", cwd="/app"
114:         )
115:         if probe.return_code != 0:
116:             await super().install(environment)
117:         await upload_delegation_policy(
118:             self, environment, default_target="/app/AGENTS.md"
119:         )
```

```text
122: class OpenCodeAgent(_HarborOpenCode):
123:     """OpenCode + optional C1 policy in ``/app/AGENTS.md``."""
124: 
125:     def __init__(self, *args: Any, **kwargs: Any) -> None:
126:         raw = os.environ.get("HARNESS_OPENCODE_CONFIG")
127:         if raw and "opencode_config" not in kwargs:
128:             config = json.loads(raw)
129:             api_key = os.environ.get("HARNESS_API_KEY")
130:             if api_key:
131:                 for provider in (config.get("provider") or {}).values():
132:                     if isinstance(provider, dict):
133:                         provider.setdefault("options", {})["apiKey"] = api_key
134:             kwargs["opencode_config"] = config
135:         super().__init__(*args, **kwargs)
136: 
137:     @override
138:     async def install(self, environment: BaseEnvironment) -> None:
139:         probe = await environment.exec(
140:             command="command -v opencode && opencode --version", cwd="/app"
141:         )
142:         if probe.return_code != 0:
143:             node_probe = await environment.exec(
144:                 command="command -v node", cwd="/app"
145:             )
146:             if node_probe.return_code != 0:
147:                 # Prepared task images are python-only; let Harbor bootstrap
148:                 # Node/OpenCode instead of assuming the shared base image.
149:                 await super().install(environment)
150:             else:
151:                 # The shared base image already has Node/npm.
152:                 await self.exec_as_agent(
153:                     environment,
154:                     command=(
155:                         "set -euo pipefail; "
156:                         "node --version; npm --version; "
157:                         "npm i -g --registry=https://registry.npmmirror.com opencode-ai@latest; "
158:                         "opencode --version"
159:                     ),
160:                 )
161:         await upload_delegation_policy(
162:             self, environment, default_target="/app/AGENTS.md"
163:         )
164: 
165:     @override
166:     async def run(
167:         self, instruction: str, environment: BaseEnvironment, context: Any
168:     ) -> None:
169:         try:
170:             await super().run(instruction, environment, context)
171:         except NonZeroAgentExitCodeError:
172:             # OpenCode can finish the final answer and then die with EPIPE while
173:             # flushing its JSON stream. Treat a logged stop as a completed run;
174:             # any other non-zero exit remains a real failure.
175:             result = await environment.exec(
176:                 command=(
177:                     "grep -q '\"type\":\"step_finish\"' /logs/agent/opencode.txt "
178:                     "&& grep -q '\"reason\":\"stop\"' /logs/agent/opencode.txt"
179:                 ),
180:                 cwd="/app",
181:             )
182:             if result.return_code != 0:
183:                 raise
```

## S02

源文件：[snapshots/harness-v3-research/harbor-agents/config/codex-model-catalog.json](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/harness-v3-research/harbor-agents/config/codex-model-catalog.json)

SHA-256：`d109a392460d2d18d57a8d2c7a67ea7e635aee2bf45eb09cd2790f730765b5ee`

解码后与 S03 文本完全相等：`True`；字符数：`20751`。

## S03

源文件：[snapshots/harness-v3-research/vendor/codex/codex-rs/models-manager/prompt.md](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/harness-v3-research/vendor/codex/codex-rs/models-manager/prompt.md)

SHA-256：`2ed1c769d32e1edd63a3b8262e28fe2e4778d5854014ec24b6780a36eaadc797`

```text
125: You are a coding agent. Please keep going until the query is completely resolved, before ending your turn and yielding back to the user. Only terminate your turn when you are sure that the problem is solved. Autonomously resolve the query to the best of your ability, using the tools available to you, before coming back to the user. Do NOT guess or make up an answer.
```

```text
149: ## Validating your work
150: 
151: If the codebase has tests or the ability to build or run, consider using them to verify that your work is complete. 
152: 
153: When testing, your philosophy should be to start as specific as possible to the code you changed so that you can catch issues efficiently, then make your way to broader tests as you build confidence. If there's no test for the code you changed, and if the adjacent patterns in the codebases show that there's a logical place for you to add a test, you may do so. However, do not add tests to codebases with no tests.
154: 
155: Similarly, once you're confident in correctness, you can suggest or use formatting commands to ensure that your code is well formatted. If there are issues you can iterate up to 3 times to get formatting right, but if you still can't manage it's better to save the user time and present them a correct solution where you call out the formatting in your final message. If the codebase does not have a formatter configured, do not add one.
```

## S04

源文件：[snapshots/harness-v3-research/vendor/codex/codex-rs/core/src/session/turn.rs](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/harness-v3-research/vendor/codex/codex-rs/core/src/session/turn.rs)

SHA-256：`52ff11062700ccbfb0b7b3c7912e7f558391c226742030a62f33f0b714e302a3`

```text
162: /// - requested function calls
163: /// - an assistant message
164: ///
165: /// While it is possible for the model to return multiple of these items in a
166: /// single sampling request, in practice, we generally one item per sampling request:
167: ///
168: /// - If the model requests a function call, we execute it and send the output
169: ///   back to the model in the next sampling request.
170: /// - If the model sends only an assistant message, we record it in the
171: ///   conversation history and consider the turn complete.
172: ///
173: pub(crate) async fn run_turn(
```

```text
580:             Ok((sampling_request_output, sampling_request_input)) => {
581:                 guardian_budget_compacted = false;
582:                 let SamplingRequestResult {
583:                     needs_follow_up: model_needs_follow_up,
584:                     last_agent_message: sampling_request_last_agent_message,
585:                 } = sampling_request_output;
586:                 if model_needs_follow_up {
587:                     sess.input_queue
588:                         .accept_mailbox_delivery_for_current_turn(
589:                             &sess.active_turn,
590:                             &turn_context.sub_id,
591:                         )
592:                         .await;
593:                 }
594:                 can_drain_pending_input = true;
595:                 // Process async hooks only after sampling and its tools have finished.
596:                 drain_async_hook_results(&sess, &turn_context, /*before_user_prompt*/ false).await;
597:                 let (has_pending_input, token_status) = async {
598:                     let has_pending_input =
599:                         sess.input_queue.has_pending_input(&sess.active_turn).await;
600:                     let token_status = super::context_window::context_window_token_status(
601:                         sess.as_ref(),
602:                         turn_context.as_ref(),
603:                     )
604:                     .await;
605:                     (has_pending_input, token_status)
606:                 }
607:                 .instrument(trace_span!("run_turn.collect_post_sampling_state"))
608:                 .await;
609:                 let needs_follow_up = model_needs_follow_up || has_pending_input;
610:                 let token_limit_reached = token_status.token_limit_reached;
```

```text
723:                 if !needs_follow_up {
724:                     last_agent_message = sampling_request_last_agent_message;
725:                     let stop_outcome = run_turn_stop_hooks(
726:                         &sess,
727:                         &step_context,
728:                         stop_hook_active,
729:                         last_agent_message.clone(),
730:                     )
731:                     .await;
732:                     if matches!(
733:                         turn_context.session_source,
734:                         SessionSource::Internal(InternalSessionSource::MemoryConsolidation)
735:                     ) && (stop_outcome.should_block || stop_outcome.should_stop)
736:                     {
737:                         // Do not feed managed rejections back into an unattended memory loop.
738:                         return Err(CodexErr::InvalidRequest(
739:                             "Memory consolidation was rejected by a Stop hook.".to_string(),
740:                         ));
741:                     }
742:                     if stop_outcome.should_block {
743:                         if let Some(hook_prompt_message) =
744:                             build_hook_prompt_message(&stop_outcome.continuation_fragments)
745:                         {
746:                             sess.record_response_item_and_emit_turn_item(
747:                                 &turn_context,
748:                                 &step_context.settings.model_info,
749:                                 hook_prompt_message,
750:                             )
751:                             .await;
752:                             sess.input_queue
753:                                 .accept_mailbox_delivery_for_current_turn(
754:                                     &sess.active_turn,
755:                                     &turn_context.sub_id,
756:                                 )
757:                                 .await;
758:                             stop_hook_active = true;
759:                             continue;
```

```text
1672: pub(crate) fn build_prompt(
1673:     input: Vec<ResponseItem>,
1674:     step_context: &StepContext,
1675:     base_instructions: BaseInstructions,
1676:     incremental_tools: bool,
1677: ) -> Prompt {
1678:     let turn_context = &step_context.turn;
1679:     Prompt {
1680:         input,
1681:         tools: if incremental_tools {
1682:             Arc::default()
1683:         } else {
1684:             step_context.tool_router.model_visible_specs()
1685:         },
1686:         parallel_tool_calls: true,
1687:         base_instructions: if incremental_tools {
1688:             BaseInstructions {
1689:                 text: String::new(),
1690:                 provenance: None,
1691:             }
1692:         } else {
1693:             base_instructions
1694:         },
```

## S05

源文件：[snapshots/harness-v3-research/vendor/opencode/packages/opencode/src/session/system.ts](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/harness-v3-research/vendor/opencode/packages/opencode/src/session/system.ts)

SHA-256：`8585edbb599cb42faeda09f406c0beae35510f88414d6580f2486e19bb0acaf9`

```text
31:     return [PROMPT_META.replaceAll("{{MODEL_NAME}}", name)]
32:   }
33:   if (model.api.id.includes("gpt-4") || model.api.id.includes("o1") || model.api.id.includes("o3"))
34:     return [PROMPT_BEAST]
35:   if (model.api.id.includes("gpt")) {
36:     if (model.api.id.includes("gpt-6")) return [PROMPT_ASTRA]
37:     if (model.api.id.includes("codex")) {
38:       return [PROMPT_CODEX]
39:     }
40:     return [PROMPT_GPT]
41:   }
42:   if (model.api.id.includes("gemini-")) return [PROMPT_GEMINI]
43:   if (model.api.id.includes("claude")) return [PROMPT_ANTHROPIC]
44:   if (model.api.id.toLowerCase().includes("trinity")) return [PROMPT_TRINITY]
45:   if (
46:     model.api.id.toLowerCase().includes("kimi") ||
47:     ["kimi-for-coding", "moonshotai", "moonshotai-cn"].includes(model.providerID)
48:   )
49:     return [PROMPT_KIMI]
50:   return [PROMPT_DEFAULT]
51: }
52: 
```

## S06

源文件：[snapshots/harness-v3-research/vendor/opencode/packages/opencode/src/session/llm/request.ts](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/harness-v3-research/vendor/opencode/packages/opencode/src/session/llm/request.ts)

SHA-256：`30797aaa349aa3d9c51aec5a37c8fb105ce3b872307fd186aa54e498986f659c`

```text
56: export const prepare = Effect.fn("LLMRequestPrep.prepare")(function* (input: PrepareInput) {
57:   const isOpenaiOauth = input.provider.id === "openai" && input.auth?.type === "oauth"
58:   const system = [
59:     [
60:       ...(input.agent.prompt ? [input.agent.prompt] : SystemPrompt.provider(input.model)),
61:       ...input.system,
62:       ...(input.user.system ? [input.user.system] : []),
63:     ]
64:       .filter((x) => x)
65:       .join("\n"),
66:   ]
67: 
68:   const header = system[0]
69:   yield* input.plugin.trigger(
70:     "experimental.chat.system.transform",
71:     { sessionID: input.sessionID, model: input.model },
72:     { system },
73:   )
74:   if (system.length > 2 && system[0] === header) {
75:     const rest = system.slice(1)
76:     system.length = 0
77:     system.push(header, rest.join("\n"))
78:   }
```

## S07

源文件：[snapshots/harness-v3-research/vendor/opencode/packages/opencode/src/session/prompt/default.txt](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/harness-v3-research/vendor/opencode/packages/opencode/src/session/prompt/default.txt)

SHA-256：`5aa623656d6d18b96b5706fceffe3a074a15db24db3a8be7169d8eb86260ce6f`

```text
70: # Doing tasks
71: The user will primarily request you perform software engineering tasks. This includes solving bugs, adding new functionality, refactoring code, explaining code, and more. For these tasks the following steps are recommended:
72: - Use the available search tools to understand the codebase and the user's query. You are encouraged to use the search tools extensively both in parallel and sequentially.
73: - Implement the solution using all tools available to you
74: - Verify the solution if possible with tests. NEVER assume specific test framework or test script. Check the README or search codebase to determine the testing approach.
75: - VERY IMPORTANT: When you have completed a task, you MUST run the lint and typecheck commands (e.g. npm run lint, npm run typecheck, ruff, etc.) with Bash if they were provided to you to ensure your code is correct. If you are unable to find the correct command, ask the user for the command to run and if they supply it, proactively suggest writing it to AGENTS.md so that you will know to run it next time.
76: NEVER commit changes unless the user explicitly asks you to. It is VERY IMPORTANT to only commit when explicitly asked, otherwise the user will feel that you are being too proactive.
77: 
78: - Tool results and user messages may include <system-reminder> tags. <system-reminder> tags contain useful information and reminders. They are NOT part of the user's provided input or the tool result.
```

## S08

源文件：[snapshots/harness-v3-research/vendor/opencode/packages/opencode/src/session/prompt.ts](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/harness-v3-research/vendor/opencode/packages/opencode/src/session/prompt.ts)

SHA-256：`53ba250a4d1e2a18527df1a35b37d375bb60907edadafb471866f325c5f68fe2`

```text
1103:           // Some providers return "stop" even when the assistant message contains
1104:           // tool calls. Keep the loop running so tool results can be sent back to
1105:           // the model, but ignore cleanup-marked interrupted orphans.
1106:           const hasToolCalls =
1107:             lastAssistantMsg?.parts.some(
1108:               (part) => part.type === "tool" && !part.metadata?.providerExecuted && !isOrphanedInterruptedTool(part),
1109:             ) ?? false
1110: 
1111:           if (
1112:             lastAssistant?.finish &&
1113:             !["tool-calls", "unknown"].includes(lastAssistant.finish) &&
1114:             !hasToolCalls &&
1115:             lastAssistant.parentID === lastUser.id
1116:           ) {
```

```text
1178:           const maxSteps = agent.steps ?? Infinity
1179:           const isLastStep = step >= maxSteps
```

```text
1264:             const system = [
1265:               ...env,
1266:               ...instructions,
1267:               ...(mcpInstructions ? [mcpInstructions] : []),
1268:               ...(skills ? [skills] : []),
1269:             ]
1270:             const format = lastUser.format ?? { type: "text" as const }
1271:             if (format.type === "json_schema") system.push(STRUCTURED_OUTPUT_SYSTEM_PROMPT)
1272:             const result = yield* handle.process({
1273:               user: lastUser,
1274:               agent,
1275:               permission: session.permission,
1276:               sessionID,
1277:               parentSessionID: session.parentID,
1278:               system,
1279:               messages: [
1280:                 ...modelMsgs,
1281:                 ...(isLastStep ? [{ role: "assistant" as const, content: MAX_STEPS_PROMPT }] : []),
1282:               ],
1283:               tools,
1284:               model,
1285:               toolChoice: format.type === "json_schema" ? "required" : undefined,
```

```text
1319:             if (result === "stop") return "break" as const
1320:             if (result === "compact") {
1321:               yield* compaction.create({
1322:                 sessionID,
1323:                 agent: lastUser.agent,
1324:                 model: lastUser.model,
1325:                 auto: true,
1326:                 overflow: !handle.message.finish,
1327:               })
1328:             }
1329:             return "continue" as const
1330:           }).pipe(
1331:             Effect.ensuring(instruction.clear(handle.message.id)),
1332:             Effect.onInterrupt(() => finalizeInterruptedAssistant),
1333:           )
1334:           if (outcome === "break") break
1335:           continue
```

## S09

源文件：[snapshots/harness-v3-research/harbor-agents/harbor_agents/framework_runner_common.py](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/harness-v3-research/harbor-agents/harbor_agents/framework_runner_common.py)

SHA-256：`5122e123eddef3a34db740a920326cfb5a007df286e2281215c376f4622e7705`

```text
116: SYSTEM_PROMPT = """You are an autonomous software and data-engineering agent running in /app.
117: Solve the user's task by inspecting and modifying the workspace with the available tools.
118: Do not merely explain a solution: create the requested files and run relevant checks.
119: All paths must remain inside /app. Continue until the task is complete, then give a concise final response.
120: """
```

## S10

源文件：[snapshots/harness-v3-research/harbor-agents/harbor_agents/langgraph_runner.py](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/harness-v3-research/harbor-agents/harbor_agents/langgraph_runner.py)

SHA-256：`740af35e41b9e9ab4cd79f88d21332fd9c470b4ccf14e6122edf8db5c2ef5e3d`

```text
223:             if not calls:
224:                 final_text = message.content or ""
225:                 break
226:             results = await asyncio.gather(*(invoke_call(call) for call in calls))
227:             messages.extend(results)
```

```text
475:     def route(state: AgentState) -> str:
476:         return "tools" if state.get("pending_calls") else END
477: 
478:     def planner_route(state: AgentState) -> str:
479:         return "parallel_workers" if state.get("plan") else "agent"
480: 
481:     builder = StateGraph(AgentState)
482:     builder.add_node("planner", planner_node)
483:     builder.add_node("agent", agent_node)
484:     builder.add_node("tools", tools_node)
485:     builder.add_node("parallel_workers", parallel_workers_node)
486:     builder.add_node("synthesizer", synthesizer_node)
487:     builder.add_edge(START, "planner")
488:     builder.add_conditional_edges(
489:         "planner",
490:         planner_route,
491:         {"agent": "agent", "parallel_workers": "parallel_workers"},
492:     )
493:     builder.add_conditional_edges("agent", route, {"tools": "tools", END: END})
494:     builder.add_edge("tools", "agent")
495:     builder.add_edge("parallel_workers", "synthesizer")
496:     builder.add_edge("synthesizer", END)
```

```text
542:     parser.add_argument("--model", required=True)
543:     parser.add_argument("--workspace", default="/app")
544:     parser.add_argument("--max-tool-iterations", type=int, default=50)
545:     parser.add_argument("--max-tokens", type=int, default=8192)
```

## S11

源文件：[snapshots/xi474-benchmark/mixed16-precise-spec-v4/tasks/reasoning4/batch_scheduler_transition_spec_v4/workspace/README.md](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/xi474-benchmark/mixed16-precise-spec-v4/tasks/reasoning4/batch_scheduler_transition_spec_v4/workspace/README.md)

SHA-256：`ba5562ac6d4c516c35f912661f31bacde0c29d11b33b44fcf990db0001c96121`

```text
24: operation：`weighted_intervals`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。
25: 
26: 输入首对象{windows:[{id:非空str,start:int>=0,end:int>start,value:int}]}，契约cooldown:int>=0。id去首尾空白后唯一；重复id即ValueError。半开区间相容条件为较早窗口end+cooldown<=较晚窗口start。输出result={selected:[排序后的规范化id],value:所选value之和}。优化顺序：总value最大；再比较排序后的整个ID列表，按通常字典序取最小，较短的相同前缀列表更小。允许负value和0值，允许空集合；若最优价值为0，空列表优于所有非空同价值列表。不得只给DP局部状态按单个ID打破平局，也不能仅因窗口value为0就一概排除它——它可能改变正价值最优解的完整ID列表平局。空windows为selected=[]、value=0。本operation只消费首输入，契约threshold不参与目标。
```

```text
55: ## 验收与执行边界
56: 
57: 在工作区运行`python3 check.py`。公开检查会清理旧outputs、完成适用的材料物化、运行run_all并检查模块与输出结构；公开通过不代表全部业务语义正确。外部只读验证器另外检查受保护文件、全部预期产物、规范序列化及接口边界输入。
```

## S12

源文件：[snapshots/xi474-benchmark/harbor-tasks-mixed16-v4/mixed16-v4-batch_scheduler_transition_spec_v4/task.toml](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/xi474-benchmark/harbor-tasks-mixed16-v4/mixed16-v4-batch_scheduler_transition_spec_v4/task.toml)

SHA-256：`cacbde7095c0089d356d254c5a7868c129cdab0e9b112e14771b1d6eac26648f`

```text
1: schema_version = "1.0"
2: version = "1.0.0"
3: artifacts = ["/app"]
4: 
5: [task]
6: name = "mixed16-v4/batch_scheduler_transition_spec_v4"
7: version = "1.0.0"
8: description = "mixed16 precise-spec v4 task: batch_scheduler_transition_spec_v4"
9: authors = [{ name = "xi474" }]
10: 
11: [metadata]
12: name = "batch_scheduler_transition_spec_v4"
13: suite = "reasoning4"
14: source = "mixed16-precise-spec-v4"
15: entry_id = "reasoning4/batch_scheduler_transition_spec_v4"
16: 
17: [verifier]
18: timeout_sec = 1800.0
19: environment_mode = "separate"
20: 
21: [agent]
22: timeout_sec = 3600.0
23: 
24: [environment]
25: build_timeout_sec = 1800.0
26: cpus = 2
27: memory_mb = 8192
28: storage_mb = 10240
```

## S13

源文件：[snapshots/harness-v3-monitoring-workspace/mixed16-v4-workflow-dag.mmd](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/harness-v3-monitoring-workspace/mixed16-v4-workflow-dag.mmd)

SHA-256：`1fad70519a673c7e406019abeb159cde5bd5fcd68b3105c59b2f26b7feddd57a`

```text
1: flowchart TD
2:   A["任务输入<br/>TASK.md + workspace/"] --> B["构建 agent 环境<br/>/app/workspace"]
3:   B --> H["Harness 选择"]
4: 
5:   H --> N["Nanobot<br/>实现 + 反复 check.py<br/>无工具调用后结束"]
6:   H --> LG["LangGraph<br/>planner → workers<br/>实现 + check.py"]
7:   H --> OC["OpenCode<br/>session 实现 + check.py<br/>session 停止后结束"]
8:   H --> CX["Codex<br/>turn 实现 + check.py<br/>turn 完成/超时后结束"]
9:   H --> DS["DSH<br/>agent team 实现 + check.py<br/>delegation_enabled (sub=0)"]
10: 
11:   N --> ART["收集最终 /app<br/>artifact 集合，只取最终状态"]
12:   LG --> ART
13:   OC --> ART
14:   CX --> ART
15:   DS --> ART
16: 
17:   ART --> V["独立 verifier 环境<br/>tests/ + trusted_validation/"]
18:   V --> I["protected_hashes 完整性校验<br/>check.py / 契约 / 输入未被篡改"]
19:   I --> HV["hidden API/向量 + 输出校验<br/>held-out cases 与 canonical 输出"]
20:   HV --> R["reward 0 / 1<br/>终结点，无反馈回路"]
21: 
22:   %% 关键：verifier 结果不返回给 agent；无 V-->H 或 V-->agent 边
```

## S14

源文件：[snapshots/harness-v3-research/harbor-agents/docker/xi474-harness-base.Dockerfile](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/harness-v3-research/harbor-agents/docker/xi474-harness-base.Dockerfile)

SHA-256：`a00204bf24bd31d26113da16b821c9a4d9889165356f7427ea88f98cddc06e7b`

```text
1: # Shared prebuilt base for the xi474 benchmark matrix.
2: #
3: # This intentionally sits on top of the existing DSH fixture image so Nanobot
4: # and DSH stay preinstalled, while Codex, OpenCode and LangGraph are baked in
5: # once instead of being installed inside every trial container.
6: FROM harness-v3-fixture-logvault-dsh:2026-10-23
7: 
8: ARG CODEX_VERSION=latest
9: ARG OPENCODE_VERSION=latest
10: ARG NPM_REGISTRY=https://registry.npmmirror.com
11: 
12: # Codex and OpenCode are CLI harnesses, not task dependencies; pin at build
13: # time and keep them in the shared layer.
14: RUN npm install -g --registry="${NPM_REGISTRY}" \
15:         "@openai/codex@${CODEX_VERSION}" \
16:         "opencode-ai@${OPENCODE_VERSION}" \
17:     && codex --version \
18:     && opencode --version
19: 
20: # Harbor's LangGraph agent checks for this exact venv path and skips its own
```

## S15

源文件：[snapshots/xi474-benchmark/mixed16-precise-spec-v4/tasks/reasoning4/batch_scheduler_transition_spec_v4/TASK.md](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/xi474-benchmark/mixed16-precise-spec-v4/tasks/reasoning4/batch_scheduler_transition_spec_v4/TASK.md)

SHA-256：`e9c5a2a695af354fbd437d5da254643fdf473c28056089f2abc1513704361131`

```text
1: # 批处理调度迁移工作区修复
2: 
3: 在带冷却期的窗口内选取迁移人员，同时计算作业关键路径和容量受限分配。补齐随附工作区的缺失Python实现，从输入重新计算全部组件结果和最终报告，仅使用Python标准库，不得硬编码产物。
4: 
5: 业务规则、输入解释、返回字段、排序及边界条件以工作区README.md和对应contract.json为准。实现各组件model.py、transform.py、render.py，以及根run_all.py和final_report.py；保留已有稳定接口。特别核对组件封装与result的区别、所有输入的消费范围、版本冲突、平局和空输入规则，以及最终摘要的完整对象范围。
6: 
7: 根据实际文件接口自行确定执行条件。完成后运行python3 check.py；不得修改任务说明、输入、契约、检查、integrate.py和物化器。公开检查只是本地检查，正式得分以工作区外的严格验证为准。
```

## S16

源文件：[snapshots/xi474-benchmark/mixed16-precise-spec-v4/tasks/reasoning4/batch_scheduler_transition_spec_v4/workspace/check.py](https://github.com/xi474/benchmark/blob/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/counterexample-review-2026-10-31/snapshots/xi474-benchmark/mixed16-precise-spec-v4/tasks/reasoning4/batch_scheduler_transition_spec_v4/workspace/check.py)

SHA-256：`a9c9e9613892bd36394d9eda29e014365e922ff67b9c9df42336083f29acc432`

```text
1: import json,subprocess,sys,shutil
2: from pathlib import Path
3: ROOT=Path(__file__).resolve().parent
4: def main():
5:     out=ROOT/'outputs'
6:     if out.is_symlink(): raise ValueError('outputs must not be a symlink')
7:     if out.exists(): shutil.rmtree(out)
8:     if (ROOT/'materialize.py').exists(): subprocess.run([sys.executable,str(ROOT/'materialize.py')],cwd=ROOT,check=True,timeout=20)
9:     for name in ['run_all.py','final_report.py']:
10:         assert (ROOT/name).is_file(), 'missing implementation: '+name
11:     subprocess.run([sys.executable,str(ROOT/'run_all.py')],cwd=ROOT,check=True,timeout=120)
12:     contracts=sorted(ROOT.rglob('contract.json'))
13:     assert contracts, 'no contracts'
14:     for path in contracts:
15:         c=json.loads(path.read_text(encoding='utf-8'))
16:         value=json.loads((ROOT/c['output']).read_text(encoding='utf-8'))
17:         assert set(value)=={'name','result'} and value['name']==c['name'] and isinstance(value['result'],dict)
18:         subprocess.run([sys.executable,str(path.with_name('check_module.py'))],cwd=path.parent,check=True,timeout=20)
19:     report=json.loads((ROOT/'outputs/final_report.json').read_text(encoding='utf-8'))
20:     assert report['component_count']==len(contracts)
21:     assert len(report['sha256'])==64 and isinstance(report['attention'],list)
22:     print('LOCAL_CHECKS_PASSED; official scoring requires the external verifier')
23: if __name__=='__main__': main()
```
