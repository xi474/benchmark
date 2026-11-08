"""Build a sanitized, certificate-selected reward-v2 metrics release."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import statistics


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def local(path):
    text = str(path)
    return Path("C:/" + text[7:] if os.name == "nt" and text.startswith("/mnt/c/") else text)


def duration(start, end):
    if not start or not end:
        return None
    delta = datetime.fromisoformat(end.replace("Z", "+00:00")) - datetime.fromisoformat(start.replace("Z", "+00:00"))
    return delta.total_seconds() if delta.total_seconds() >= 0 else None


def write_csv(path, rows):
    if not rows:
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict,list)) else v
                          for k,v in row.items()} for row in rows)


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Export:
    def __init__(self, outputs, monitor, destination):
        self.root, self.dest = outputs.resolve(), destination
        self.matrix = self.root / "reward-v2-v4pro-matrix210-20261104"
        self.medium = self.root / "reward-v2-v4pro-medium26-seven-arm-20261105"
        self.roma = self.root / "reward-v2-v4pro-roma-replacement-20261106"
        spec = importlib.util.spec_from_file_location("api", monitor / "scripts/aggregate_verify_api_accuracy.py")
        self.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.api)
        self.index = self.api.score_index([self.matrix, self.medium, self.roma])
        self.paths, self.sources, self.loops = {}, {}, []

    def locator(self, path):
        return Path(path).resolve().relative_to(self.root).as_posix()

    def pin(self, path):
        self.sources[self.locator(path)] = digest(path)

    def cell(self, arm, task, tid, classification, reward, maximum, source, result=None, score_hash=None, **extra):
        self.pin(source)
        paths = [local(result).parent / "verifier/score-v2.json"] if result else self.index.get(tid, [])
        if len(paths) != 1 or not paths[0].is_file():
            raise ValueError("Missing or ambiguous score for " + tid)
        if score_hash and digest(paths[0]) != score_hash:
            raise ValueError("Certified score hash mismatch for " + tid)
        self.index[tid], self.paths[tid] = paths, paths[0]
        return dict(arm=self.api.arm_name(arm), task=task, dataset=self.api.dataset(task), trial_id=tid,
                    classification=classification, certified_reward=reward, certified_max_reward=maximum,
                    certificate_path=self.locator(source), certificate_sha256=digest(source), **extra)

    def collect(self):
        cells = []
        for path in (self.matrix / "stage1-completion-audit.json",
                     self.matrix / "stage2-completion-audit-r4.json",
                     self.medium / "five-harnesses-completion-audit-r6.json"):
            cert = read(path)
            selected = cert["cells"] if isinstance(cert["cells"], list) else cert["selected"]
            for c in selected:
                cells.append(self.cell(c.get("harness",cert.get("harness")), c["task"], c["trial_id"],
                                       c["classification"], c["reward"], c["max_reward"], path,
                                       c.get("result_path"), c.get("score_v2_sha256")))
        if len(cells) != 310:
            raise ValueError("Historical certificate count differs")
        path = self.medium / "latte-adapted-after-five-merge-r1/outcomes.json"
        for tid, o in read(path).items():
            ev = o["result_evidence"]
            if ev["passed"] is not True:
                raise ValueError("LATTE Medium26 monitoring evidence incomplete")
            e = ev["evaluation"]
            cls = e["status"]
            if cls == "scored" and o.get("exception"):
                cls = "scored_with_agent_nonzero_exit"
            cells.append(self.cell("latte-planning-adapted", e["task"], tid, cls,
                                   e["reward"], e["max_reward"], path, o["result_path"],
                                   ev["artifact_sha256"]["score-v2.json"]))
        stage = self.roma / "roma-medium26-remaining12-r6-skippable-audited"
        cert_path = stage / "medium26-merged-audit.json"
        cert = read(cert_path)
        for path, key in ((self.roma / "roma-medium26-r5-http4-audited/outcomes.json", "old_r5_outcomes_sha256"),
                          (stage / "outcomes.json","r6_outcomes_sha256")):
            if digest(path) != cert[key]:
                raise ValueError("ROMA Medium26 certificate source drift")
            self.pin(path)
            for o in read(path).values():
                trial = local(o["result_path"]).parent
                score = read(trial / "verifier/score-v2.json")
                cls = "skipped_pre_send_budget_cap" if o["task"] == "medium/MP14" else o["classification"]
                cells.append(self.cell("roma",o["task"],trial.parent.name,cls,score["reward"],score["max_reward"],
                                       cert_path,o["result_path"],o.get("score_v2_sha256"),
                                       transport_variant="C0-json-object-http4"))
        path = self.roma / "roma-original30-remaining24-r9-queue-recovery/original30-merged-audit.json"
        cert = read(path)
        for o in cert["selected"]:
            trial = local(o["result_path"]).parent
            score = read(trial / "verifier/score-v2.json")
            cells.append(self.cell("roma",o["task"],trial.parent.name,o["classification"],
                                   score["reward"],score["max_reward"],path,o["result_path"],o["score_v2_sha256"],
                                   transport_variant="C0-json-instruction-v1-http4"))
        if len(cells) != 392 or len({(c["arm"],c["task"]) for c in cells}) != 392:
            raise ValueError("Expected 392 unique baseline cells")
        repeats = []
        queue = self.roma / "roma-original30-remaining24-r9-queue-recovery/queue-completion.json"
        if len(read(queue)["latte_cells"]) != 4:
            raise ValueError("Continuation queue not complete")
        self.pin(queue)
        for i in range(1,5):
            path = self.matrix / f"stage2-latte-mixed16-invalid-repeat-r2-cell{i:02d}/trial-audit.json"
            c = read(path)
            score = read(local(c["result_path"]).parent / "verifier/score-v2.json")
            repeats.append(self.cell("latte-planning-adapted",c["task"],c["trial_id"],c["classification"],
                                     c["reward"],score["max_reward"],path,c["result_path"],
                                     repeat_of_trial_id=c["repeat_of_trial_id"]))
        return cells,repeats

    @lru_cache(maxsize=None)
    def receipts(self, path):
        grouped = defaultdict(list)
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                grouped[row.get("trial_id")].append(row)
        return grouped

    def usage(self, trial, row):
        path = trial / "agent/telemetry/http-requests.json"
        if row["arm"] == "roma":
            records = read(path)["requests"]
            sent = [r for r in records if r["state"] in ("sent","completed")]
            done = [r for r in sent if r["state"] == "completed"]
            ids = [r["http_request_id"] for r in sent]
            if len(ids) != len(set(ids)):
                raise ValueError("Duplicate native usage identities")
            usages = [r for r in done]
            unknown = len(sent)-len(done)
            cache = [r.get("cache_tokens") for r in done]
            cost = sum(Decimal(r["input_tokens"])*Decimal("1.32")+Decimal(r["output_tokens"])*Decimal("3.96")
                       -Decimal(r.get("cache_tokens") or 0)*Decimal("1.276") for r in done)/1000000
            observed = len(sent)
            source = "native-actual-http-journal"
            before_send = len(records)-len(sent)
        else:
            gateway = next((p/"gateway-requests.jsonl" for p in trial.parents
                            if (p/"gateway-requests.jsonl").is_file()),None)
            if gateway is None:
                return dict(tokens_source="unavailable",tokens_status="unavailable")
            groups = self.receipts(str(gateway))
            records = groups.get(row["trial_id"], groups.get(trial.parent.name,[]))
            settled = {}
            for r in records:
                if r.get("type") == "settled":
                    if r["request_id"] in settled and settled[r["request_id"]] != r:
                        raise ValueError("Conflicting duplicate settled usage")
                    settled[r["request_id"]] = r
            done = list(settled.values())
            sent_ids = {r["request_id"] for r in records if r.get("type") == "reserved"}
            unknown_ids = {r["request_id"] for r in records if r.get("type") == "unknown"}
            if not done or set(settled)-sent_ids:
                return dict(tokens_source="gateway-trial-match-unavailable",tokens_status="unavailable")
            sent, unknown = list(sent_ids), len(unknown_ids | (sent_ids-set(settled)))
            usages = [r["usage"] for r in done]
            cache = [u.get("cache_tokens") for u in usages]
            cost = sum(Decimal(str(r["estimated_peak_usd"])) for r in done)
            observed = len({r["request_id"] for r in records if r.get("type")=="request-observation"})
            before_send = None
            source = "deduplicated-actual-gateway-settled-receipts"
        def ordinary_mode(record):
            if str(record.get("path", "")).endswith("/responses"):
                return record.get("thinking_type") == "none" and record.get("reasoning_effort") == "none"
            return record.get("thinking_type") == "disabled"
        if any(r.get("requested_model")!="deepseek-v4-pro" or not ordinary_mode(r) for r in done):
            raise ValueError("Actual model/mode differs for " + row["trial_id"] + ": "
                             + repr({(r.get("requested_model"), r.get("thinking_type")) for r in done}))
        inp = sum(u["input_tokens"] for u in usages)
        out = sum(u["output_tokens"] for u in usages)
        cached = sum(v for v in cache if isinstance(v,int))
        return dict(model_requests_sent=len(sent),model_requests_settled=len(done),model_requests_unknown=unknown,
                    tokens_input=inp if not unknown else None,tokens_output=out if not unknown else None,
                    tokens_total=inp+out if not unknown else None,
                    tokens_input_known=inp,tokens_output_known=out,tokens_cache_hit_known=cached,
                    cache_usage_complete=all(isinstance(v,int) for v in cache),
                    tokens_status="observed" if not unknown else "partial_unknown_request",
                    tokens_source=source,request_observations=observed,
                    request_hash_observed=sum(len(r.get("request_sha256",""))==64 for r in done),
                    blocked_before_send_count=before_send,estimated_settled_peak_usd=float(cost))

    def metrics(self,row):
        score_path = self.paths[row["trial_id"]]
        trial = score_path.parent.parent
        result = read(trial / "result.json")
        row.update(e2e_seconds=duration(result.get("started_at"),result.get("finished_at")),
                   agent_exception=(result.get("exception_info") or {}).get("exception_type"),
                   result_locator=self.locator(trial/"result.json"),
                   result_sha256=digest(trial/"result.json"))
        for name in ("agent_execution","verifier","environment_setup","agent_setup"):
            phase = result.get(name) or {}
            row[name+"_seconds"] = duration(phase.get("started_at"),phase.get("finished_at"))
        row.update(self.usage(trial,row))
        path = next((p for p in (trial/"agent/monitoring/native-telemetry/summary.json",
                                 trial/"agent/telemetry/summary.json") if p.exists()),None)
        summary = read(path) if path else {}
        row.update(orchestration_status=summary.get("orchestration_status"),
                   observed_subagent_count_reported=summary.get("subagent_count"),
                   autonomous_delegation_reported=summary.get("autonomous_delegation"),
                   tool_calls_reported=summary.get("tool_call_count",summary.get("tool_calls_requested")),
                   planning_level=summary.get("planning_level"),
                   telemetry_summary_sha256=digest(path) if path else None)
        resources = next((p for p in (trial/"agent/matrix-resources.csv",
                                      trial/"agent/telemetry/resources.csv") if p.exists()),None)
        samples = []
        if resources:
            with resources.open(encoding="utf-8-sig",newline="") as stream:
                samples = list(csv.DictReader(stream))
        def numeric_column(name):
            values = []
            for sample in samples:
                try:
                    value = int(sample[name])
                    if value >= 0:
                        values.append(value)
                except (ValueError,TypeError,KeyError):
                    pass
            return values
        memory,cpu = numeric_column("memory_current_bytes"),numeric_column("cpu_usage_usec")
        row.update(resource_samples=len(samples) if resources else None,
                   peak_sampled_container_memory_bytes=max(memory) if memory else None,
                   container_cpu_delta_seconds=(max(cpu)-min(cpu))/1000000 if cpu else None,
                   resource_scope="task-container" if resources else None)
        native = summary.get("roma_structure") or {}
        for key in ("actual_child_solve_instances","recursive_subplans","leaf_executor_parallel_width",
                    "model_http_parallel_width","tool_parallel_width","runtime_created_agent_definitions"):
            row["roma_"+key] = native.get(key)
        path = next((p for p in (trial/"agent/monitoring/native-telemetry/tool-concurrency-trace.json",
                                 trial/"agent/telemetry/tool-concurrency-trace.json") if p.exists()),None)
        tool = read(path).get("summary",{}) if path else {}
        for key in ("complete_span_count","failed_span_count","max_concurrent_tools","observed_active_tool_time_ms","timing_quality"):
            row["tool_"+key] = tool.get(key)
        path = next((p for p in (trial/"agent/monitoring/outcome-loops.json",
                                 trial/"agent/telemetry/outcome-loops.json") if p.exists()),None)
        loops = read(path) if path else {}
        correlated = loops.get("correlated_check_loops")
        row["self_check_correlated_loops"] = len(correlated) if isinstance(correlated,list) else None
        row["duplicate_usage_records_observed"] = loops.get("duplicate_usage_records")
        for key in ("sent","parent_received","entered_model_request"):
            row["delivery_"+key] = (loops.get("delivery_summary") or {}).get(key)
        for n, loop in enumerate(correlated or [],1):
            record = dict(arm=row["arm"],dataset=row["dataset"],task=row["task"],trial_id=row["trial_id"],loop_number=n)
            for key in ("classification","analysis_of_failure_observed","model_input_contains_failed_result",
                        "recheck_passed","post_failure_window_ms","observation_window_ms","timing_basis",
                        "pure_self_reflection_incremental_cost_usd"):
                record[key] = loop.get(key)
            for key in ("model_timing","fix_tool_timing","recheck_timing"):
                record[key+"_union_ms"] = (loop.get(key) or {}).get("union_ms")
            self.loops.append(record)
        row["score_path"] = self.locator(score_path)
        return row

    def analyze(self,cells):
        rows = self.api.analyze(cells,self.index)
        for row in rows:
            row["raw_api_accuracy"],row["raw_focused_accuracy"] = row["api_accuracy"],row["focused_accuracy"]
            if row["classification"] in {"skipped_pre_send_budget_cap","evidence_failed","quarantined","infrastructure_or_monitoring_failure"}:
                row.update(api_accuracy=None,focused_accuracy=None,api_accuracy_status="unscored_"+row["classification"])
            self.metrics(row)
        return rows

    def summaries(self,rows):
        summaries = self.api.summarize(rows)
        for s in summaries:
            group = [r for r in rows if (r["arm"],r["dataset"])==(s["arm"],s["dataset"])]
            comparable = [r for r in group if r["score_status"]=="scored" and not r["api_accuracy_status"].startswith("unscored_")]
            times = [r["e2e_seconds"] for r in group if r["e2e_seconds"] is not None]
            s.update(classification_counts=dict(Counter(r["classification"] for r in group)),
                     comparable_reward_sum=sum(r["certified_reward"] for r in comparable),
                     comparable_reward_max_sum=sum(r["certified_max_reward"] for r in comparable),
                     all_checks_passed_cells=sum(r["all_checks_passed"] is True for r in comparable),
                     e2e_observed_cells=len(times),
                     e2e_mean_seconds=statistics.mean(times) if times else None,
                     e2e_median_seconds=statistics.median(times) if times else None,
                     tokens_observed_cells=sum(r["tokens_status"]=="observed" for r in group),
                     tokens_unavailable_cells=sum(r["tokens_status"]=="unavailable" for r in group),
                     tokens_input_known_sum=sum(r.get("tokens_input_known") or 0 for r in group),
                     tokens_output_known_sum=sum(r.get("tokens_output_known") or 0 for r in group),
                     tokens_cache_hit_known_sum=sum(r.get("tokens_cache_hit_known") or 0 for r in group),
                     model_requests_unknown=sum(r.get("model_requests_unknown") or 0 for r in group),
                     estimated_settled_peak_usd=sum(r.get("estimated_settled_peak_usd") or 0 for r in group),
                     resource_observed_cells=sum((r.get("resource_samples") or 0)>0 for r in group),
                     self_check_observed_cells=sum(r.get("self_check_correlated_loops") is not None for r in group),
                     self_check_correlated_loops=sum(r.get("self_check_correlated_loops") or 0 for r in group))
        return summaries

    def report(self,summary,repeats):
        pct = lambda v: "不适用" if v is None else f"{100*v:.2f}%"
        lines = [
            "# DeepSeek V4 Pro 普通模式 reward-v2 七 Harness 结果","",
            "基线共392个唯一题位，每个Harness包含原14题、mixed16-v4的16题、Medium26的26题。LATTE四次独立补跑另列附表，原baseline保留。","",
            "| Harness | 数据集 | 题位 | API有效题数 | API微平均 | API宏平均 | 平均e2e秒 | 输入tokens已知部分 | 输出tokens已知部分 |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for s in summary:
            lines.append(f"| {s['arm']} | {s['dataset']} | {s['certified_cells']} | {s['api_measured_cells']} | {pct(s['api_micro_accuracy'])} | {pct(s['api_macro_accuracy'])} | {s['e2e_mean_seconds']:.2f} | {s['tokens_input_known_sum']} | {s['tokens_output_known_sum']} |")
        lines += ["","api_accuracy为verifier中api/检查通过数除以总数。原14题无api/分母，另列focused/通过率。无效提交、预算截断与基础设施证据失败保留原始检查数，可比较API比率为null。有效的超时、输出上限和Harbor汇总异常评分保留异常标签。","",
                  "e2e从Harbor trial的started_at到finished_at，包含环境准备、Agent执行和verifier。分阶段时间另列。批次包含5/8并发及ROMA单Harbor/HTTP4，时间属于各自资源条件下的观测，不能直接归因于Harness本身。",
                  "tokens来自去重后的实际上游结算记录。缓存命中tokens为输入的子集。未知请求保留未知，完整token总量为null，已结算部分另列。费用为注册峰价或原账本估算，invoice未观测。",
                  "资源采用task-container采样。工具并发仅在执行边界可配对时报告。Agent定义、递归Solve实例、委派计数按源监控保留。ROMA原30题使用JSON指令v1传输适配，Medium26沿用早期C0 JSON-object条件。LATTE为planning-adapted。",
                  "self-check-loops.csv记录失败后分析、修复和复验的关联窗口。观察窗口与执行时间分别列出，窗口可能重叠。缺失span、不可比时钟和纯自检增量成本保留null。","",
                  "ROMA原30题含24个普通scored、1个scored_with_harbor_summary_error、4个预算跳过和1个证据失败；Medium26为25个scored加1个预算跳过。","",
                  "| LATTE独立补跑任务 | 分类 | reward / max | API通过数 / 总数 | API准确率 |","|---|---|---:|---:|---:|"]
        for r in repeats:
            lines.append(f"| {r['task']} | {r['classification']} | {r['certified_reward']} / {r['certified_max_reward']} | {r['api_passed']} / {r['api_total']} | {pct(r['api_accuracy'])} |")
        lines += ["","中断修复涉及ROMA JSON模式提示、Docker退出后的隔离续跑、Harbor临时目录尾部下划线引发的汇总打印异常，以及LATTE四题唯一ID误比较26的门禁。传输IncompleteRead用量未知和输入token发送前预算截断均已隔离留证，随后继续队列。",
                  "历史ROMA R6 HTTP400、R7 Docker中断、LATTE R3 HTTP402各有1次未知用量，历史Codex29 HTTP402用量也未知，跨批费用总账仍不完整。","",
                  "发布包仅含结构化指标、公开任务标识、证据SHA256和可移植定位符。原始日志、提示、工具输出、私有数据、凭据和LATTE源码均未包含。"]
        return "\n".join(lines)+"\n"

    def run(self):
        cells,repeated = self.collect()
        rows,repeats = self.analyze(cells),self.analyze(repeated)
        groups = Counter((r["arm"],r["dataset"]) for r in rows)
        for arm in {r["arm"] for r in rows}:
            for group,n in (("original14",14),("mixed16-v4",16),("medium26",26)):
                if groups[(arm,group)] != n:
                    raise ValueError("Per-dataset matrix count differs")
        summary = self.summaries(rows)
        self.dest.mkdir(parents=True,exist_ok=False)
        write_csv(self.dest/"cells-392.csv",rows)
        write_csv(self.dest/"summary-21.csv",summary)
        write_csv(self.dest/"latte-independent-repeats-4.csv",repeats)
        write_csv(self.dest/"self-check-loops.csv",self.loops)
        write_json(self.dest/"results.json",dict(schema="harness.reward-v2.metrics/1",baseline_cells=rows,
                                                summary=summary,latte_independent_repeats=repeats))
        for group in ("mixed16-v4","medium26"):
            matrix = defaultdict(dict)
            for r in rows:
                if r["dataset"] == group:
                    matrix[r["task"]][r["arm"]] = f"{r['api_passed']}/{r['api_total']} ({100*r['api_accuracy']:.2f}%)" if r["api_accuracy"] is not None else r["api_accuracy_status"]
            write_csv(self.dest/f"api-task-matrix-{group}.csv",[dict(task=k,**v) for k,v in sorted(matrix.items())])
        (self.dest/"README.md").write_text(self.report(summary,repeats),encoding="utf-8")
        write_json(self.dest/"audit.json",dict(schema="harness.reward-v2.public-export-audit/1",
            baseline_cells=392,independent_repeats=4,model="deepseek-v4-pro",mode="non-thinking",
            classification_counts=dict(Counter(r["classification"] for r in rows)),
            api_status_counts=dict(Counter(r["api_accuracy_status"] for r in rows)),
            source_artifact_sha256=self.sources,exporter_sha256=digest(Path(__file__)),
            artifact_sha256={p.name:digest(p) for p in self.dest.iterdir() if p.is_file()}))
        print(json.dumps(dict(cells=len(rows),summaries=len(summary),repeats=len(repeats),
                             tokens_status=dict(Counter(r["tokens_status"] for r in rows)),
                             api_status=dict(Counter(r["api_accuracy_status"] for r in rows)),
                             destination=str(self.dest)),ensure_ascii=False))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--outputs-root",type=Path,required=True)
    p.add_argument("--monitor-root",type=Path,required=True)
    p.add_argument("--destination",type=Path,required=True)
    a=p.parse_args()
    Export(a.outputs_root,a.monitor_root,a.destination).run()
