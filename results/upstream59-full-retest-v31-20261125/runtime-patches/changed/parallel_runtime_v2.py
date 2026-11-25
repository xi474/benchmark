"""Narrow runtime hooks for v2. Existing v1 control types remain unchanged."""
import copy
import json
import hashlib
import os
from dataclasses import asdict, replace

from .parallel_control_v2 import DecisionContextV2, V2_TOOL
from .planning import InvalidTaskPlan, SPAWN_SUBTASKS_TOOL_NAME
from .classifier_input_v2 import project_context
from .classifier_state_memory import RuntimeClassifierState, is_contract_path
from .dynamic_frontier import canonical_work_unit_id
from .g1_discovery import contract_heuristics_enabled


def _result_ok(result):
    return isinstance(result, dict) and result.get("ok") is not False and result.get("returncode", 0) == 0


def _normalized_path(value):
    path = str(value or "").replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path.lstrip("/")


def _is_probe_only_shell(command):
    """Recognize environment/inventory probes that do not advance task state."""

    text = " ".join(str(command or "").lower().split())
    return any(token in text for token in (
        "git status", "git log", "get-childitem", "dir /s", "findstr",
        ".rglob(", "pathlib.path('.').rglob", "where.exe", "which ", "pwd",
    ))


def _tool_observations(messages):
    # Some OpenAI-compatible gateways reuse the same id for several calls.
    # Pair each tool result with its own arguments, in arrival order.
    arguments = {}
    observations = []
    for message in messages:
        if message.get("role") == "assistant":
            for call in message.get("tool_calls") or []:
                function = call.get("function", {})
                raw = function.get("arguments", {})
                try:
                    value = json.loads(raw) if isinstance(raw, str) else raw
                except (TypeError, ValueError):
                    value = {"invalid_arguments": True}
                arguments.setdefault(call["id"], []).append(value)
        elif message.get("role") == "tool":
            try:
                result = json.loads(message["content"])
            except (TypeError, ValueError):
                result = {"text": message.get("content", "")}
            if isinstance(result, dict) and result.get("v2_protocol_error"):
                continue
            # Preserve real branch deliveries; exclude control acknowledgements.
            if (message.get("name") == V2_TOOL
                    and not (isinstance(result, dict) and "subtasks" in result)):
                continue
            queued_arguments = arguments.get(message["tool_call_id"], [])
            call_arguments = queued_arguments.pop(0) if queued_arguments else {}
            observations.append({"evidence_id": message["tool_call_id"],
                "tool": message.get("name", ""),
                "arguments": call_arguments, "result": result})
    return observations


class ParallelRuntimeV2Mixin:
    def _g1_discovery_inventory(self, state):
        from .g1_discovery import build_discovery_inventory
        if not contract_heuristics_enabled():
            return build_discovery_inventory()
        memory = getattr(self, "_v2_classifier_state_memory", None)
        return build_discovery_inventory(
            verified_state=memory.snapshot(state.task) if memory is not None else {},
            messages=state.messages,
        )

    def _g1_discovery_checkpoint(self):
        from .g1_discovery import DiscoveryCheckpoint
        checkpoint = getattr(self, "_g1_discovery_state", None)
        if checkpoint is None:
            checkpoint = self._g1_discovery_state = DiscoveryCheckpoint()
        return checkpoint

    def _v2_before_request(self, state, node_id):
        """Only this boundary evaluates. step is the last completed model turn."""
        offer = state.pending_v2_offer
        if offer is not None and state.step + 1 > offer.expires_after_step:
            self._v2_close_offer(state, "expired_without_explicit_decision")
        # A semantic handshake is a small transaction: do not evaluate the
        # stale pre-report frontier while waiting for its report-only turn.
        if state.v2_frontier_handshake_pending:
            return node_id
        return self._observe_v2(state, node_id, state.v2_next_event)

    def _v2_project_tool_evidence(self, state):
        """Project current tool facts without advancing the committed frontier."""
        memory = getattr(self, "_v2_classifier_state_memory", None)
        projected = copy.deepcopy(memory) if memory is not None else RuntimeClassifierState()
        projected.merge_observations(
            [row for row in _tool_observations(state.messages)
             if row["tool"] != "report_frontier_state"],
            state.step,
        )
        return projected

    def _v2_snapshot_for_h3_report(self, state):
        return self._v2_project_tool_evidence(state).snapshot(state.task)

    def _v2_remaining_expansion_budget(self, state):
        controller = self.parallel_controller_v2
        return min(
            self.max_plan_expansions - state.plan_expansion_count,
            controller.config.max_expansions - state.v2_expansion_count,
        )

    def _v2_schedule_frontier_handshake(self, state, reason):
        """Schedule one report-only turn for a proven semantic boundary."""

        controller = self.parallel_controller_v2
        if (
            controller.mode == "off"
            or self._guard_serial_selfcheck(state)
            or self.depth != 0
            or not self.allow_initial_subtasks
            or state.pending_v2_offer is not None
            or self._v2_remaining_expansion_budget(state) < 1
        ):
            return False
        if state.v2_frontier_handshake_pending:
            return False
        state.v2_frontier_handshake_generation += 1
        state.v2_frontier_handshake_pending = True
        state.v2_frontier_handshake_reason = str(reason)
        self.tracer.emit(
            "parallel_v2_frontier_handshake_scheduled",
            step=state.step,
            task_id=state.task_id,
            scope_id=self.scope_id,
            generation=state.v2_frontier_handshake_generation,
            reason=state.v2_frontier_handshake_reason,
        )
        return True

    @staticmethod
    def _v2_successful_write_signatures(calls, results):
        signatures = {}
        for call, result in zip(calls, results):
            if call.name not in {"write_file", "write_file_chunk", "edit_file", "apply_patch"}:
                continue
            if not _result_ok(result):
                continue
            path = _normalized_path(result.get("path") or call.arguments.get("path"))
            if path:
                body = [
                    call.name,
                    path,
                    call.arguments.get("content", call.arguments.get("patch", "")),
                    result.get("sha256") or result.get("file_sha256") or "",
                ]
                signatures[path] = hashlib.sha256(
                    json.dumps(body, ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest()
            for value in result.get("materialized_paths") or ():
                normalized = _normalized_path(value)
                if normalized:
                    signatures[normalized] = hashlib.sha256(
                        json.dumps(
                            [call.name, normalized, result],
                            ensure_ascii=False,
                            sort_keys=True,
                            default=str,
                        ).encode()
                    ).hexdigest()
        return signatures

    @staticmethod
    def _v2_successful_evidence_batch_signature(calls, results):
        """Return a stable digest for one genuinely new root evidence batch.

        This is deliberately tool- and path-agnostic.  The earlier trigger only
        recognized contract-like filenames, so ordinary README/source/test
        reads and writes could never request a frontier commit.  Control calls,
        deferred calls, and Runtime-suppressed duplicates are not new evidence
        and must not recursively create handshakes.
        """

        control_tools = {
            SPAWN_SUBTASKS_TOOL_NAME,
            V2_TOOL,
            "choose_execution_mode",
            "report_frontier_state",
        }
        rows = []
        for call, result in zip(calls, results):
            if call.name in control_tools or not _result_ok(result):
                continue
            if any(result.get(marker) for marker in (
                "deferred",
                "duplicate_in_same_turn",
                "duplicate_no_new_evidence",
                "duplicate_tool_circuit_breaker",
            )):
                continue
            row = json.dumps(
                [call.name, call.arguments, result],
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
            rows.append(hashlib.sha256(row.encode()).hexdigest())
        if not rows:
            return ""
        return hashlib.sha256(
            json.dumps(rows, ensure_ascii=False).encode()
        ).hexdigest()

    def _v2_arm_post_join_watch(self, state, frontier):
        """Watch the one immediate producer reported after a semantic join."""

        state.v2_post_join_watch_paths = ()
        state.v2_post_join_followup_available = False
        safe = list(frontier.get("ready_candidates") or [])
        safe_ids = set(frontier.get("safe_candidate_ids") or [])
        safe = [item for item in safe if item.get("id") in safe_ids]
        if len(safe) != 1 or self._v2_remaining_expansion_budget(state) < 1:
            return
        candidate = safe[0]
        contract = candidate.get("completion_contract") or {}
        raw_paths = list(contract.get("required_artifact_paths") or [])
        if not raw_paths:
            raw_paths = list(candidate.get("write_set") or [])
        paths = tuple(sorted({
            _normalized_path(path) for path in raw_paths if _normalized_path(path)
        }))
        if not paths:
            return
        state.v2_post_join_watch_paths = paths
        state.v2_post_join_followup_available = True
        self.tracer.emit(
            "parallel_v2_post_join_watch_armed",
            step=state.step,
            task_id=state.task_id,
            scope_id=self.scope_id,
            watched_paths=list(paths),
            candidate_id=candidate.get("id"),
        )

    def _v2_fact_digest(self, context):
        memory = context.frontier_memory or {}
        # Trace-node counters and last_event also change after a control-only
        # offer response.  They are not new task facts and previously caused an
        # immediately declined offer to be emitted again.  Retain only state
        # that can change semantic readiness; real branch/join changes are also
        # covered by dag_nodes inside evidence_digest.
        stable_memory = {
            key: memory.get(key)
            for key in (
                "join_pending", "has_failed_predecessor", "has_missing_input",
                "has_write_conflict", "shared_write_conflicts",
            )
            if key in memory
        }
        classifier = memory.get("verified_classifier_state") or {}
        contract = classifier.get("verified_contract_state") or {}
        frontier = classifier.get("dynamic_frontier") or {}

        # Trigger on decision-state changes, not every new shell output.  A
        # long inspection can read different slices or rows from the same
        # input dozens of times without changing the executable frontier.
        # The frontier builder absorbs path, write, delivery, and LLM-delta
        # changes into one version.  Raw trace growth no longer causes calls.
        semantic_classifier_state = {
            "frontier_version": frontier.get("frontier_version", ""),
            "safe_candidate_ids": frontier.get("safe_candidate_ids", []),
            "safe_width": frontier.get("safe_width", 0),
            "contract": {
                "status": contract.get("status", "unseen"),
            },
        }
        body = [semantic_classifier_state, stable_memory, context.dag_nodes,
                context.expansions, context.remaining_expansions,
                context.maximum_width, context.pending_offer]
        return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def _v2_verified_evidence_digest(self, context):
        """Hash only execution facts that can legitimately invalidate an offer.

        The LLM-authored frontier summary may change after an invalid response,
        even though no tool ran and no branch completed.  It is useful predictor
        input, but it is not verified evidence and must not close a pending offer.
        """
        latest = {}
        opaque_side_effects = []
        for row in context.observations:
            args = row.get("arguments", {})
            result = row.get("result", {})
            tool = row.get("tool", "")
            if not _result_ok(result):
                # Failed probes and failed writes are useful diagnostic input,
                # but they do not materialize a new executable frontier.
                continue
            if self.tools.metadata(tool, args).read_only:
                if tool == "read_file":
                    key_body = [tool, _normalized_path(result.get("path") or args.get("path"))]
                elif tool == "list_files":
                    key_body = [tool, _normalized_path(args.get("path") or "."), bool(args.get("recursive"))]
                else:
                    key_body = [tool, args]
                key = json.dumps(key_body, sort_keys=True, ensure_ascii=False)
                latest[key] = json.dumps(result, sort_keys=True, ensure_ascii=False)
            elif tool in {"write_file", "write_file_chunk", "edit_file", "apply_patch"}:
                path = _normalized_path(result.get("path") or args.get("path"))
                key = json.dumps(["workspace_write", path], ensure_ascii=False)
                value = {
                    "path": path,
                    "content": args.get("content", args.get("patch", "")),
                    "result": result,
                }
                latest[key] = json.dumps(value, sort_keys=True, ensure_ascii=False)
            elif tool == "shell":
                command = " ".join(str(args.get("command", "")).split())
                if _is_probe_only_shell(command):
                    continue
                key = json.dumps(["shell", command], ensure_ascii=False)
                latest[key] = json.dumps({
                    "returncode": result.get("returncode", 0),
                    "output": result.get("output", ""),
                }, sort_keys=True, ensure_ascii=False)
            else:
                key = json.dumps([tool, args], sort_keys=True, ensure_ascii=False)
                value = json.dumps(result, sort_keys=True, ensure_ascii=False)
                # Unknown mutating tools may have invisible effects, so retain
                # occurrence ordering conservatively.
                opaque_side_effects.append([key, value])
        body = [context.task, sorted(latest.items()), opaque_side_effects, context.dag_nodes,
                context.tool_names, context.expansions, context.remaining_expansions,
                context.maximum_width, context.allowed_validator_refs]
        return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def _v2_semantic_checkpoint_deferred_ordinals(self, state, calls):
        """Defer post-contract mutations so readiness can be re-evaluated.

        A model may emit a shared contract write and all of its downstream
        consumer writes in one tool batch. Executing the whole batch erases the
        observable boundary where a parallel frontier first becomes concrete.
        This narrow barrier executes contract materialization, while deferring
        later mutations to the next request boundary. It never invents a DAG or
        reorders an accepted child plan.
        """

        controller = self.parallel_controller_v2
        if (contract_heuristics_enabled() and controller.mode == "active"
                and self.depth == 0 and self.allow_initial_subtasks
                and state.pending_v2_offer is None
                and self._v2_remaining_expansion_budget(state) > 0):
            inventory = self._g1_discovery_inventory(state)
            deferred = self._g1_discovery_checkpoint().defer_before_write(
                inventory, calls, depth=self.depth,
                serial_selfcheck=self._guard_serial_selfcheck(state))
            if deferred:
                self._v2_schedule_frontier_handshake(state, "g1_before_first_business_write")
                self.tracer.emit(
                    "g1_prewrite_discovery_checkpoint", scope_id=self.scope_id,
                    step=state.step, evidence_digest=inventory["evidence_digest"],
                    interface_count=inventory["interface_count"],
                    deferred_call_ids=[calls[index].id for index in sorted(deferred)],
                    not_executed=True)
                return deferred
        if controller.mode != "active" or self.depth != 0 or len(calls) < 2:
            return frozenset()
        control_tools = {SPAWN_SUBTASKS_TOOL_NAME, V2_TOOL, "choose_execution_mode"}
        if any(call.name in control_tools for call in calls):
            return frozenset()
        contract_writes = {
            index for index, call in enumerate(calls)
            if call.name in {"write_file", "write_file_chunk", "edit_file", "apply_patch"}
            and is_contract_path(call.arguments.get("path"))
        }
        watched = set(state.v2_post_join_watch_paths)
        watched_writes = {
            index for index, call in enumerate(calls)
            if call.name in {"write_file", "write_file_chunk", "edit_file", "apply_patch"}
            and _normalized_path(call.arguments.get("path")) in watched
        }
        boundary_writes = contract_writes | watched_writes
        if not boundary_writes:
            return frozenset()
        other_mutations = {
            index for index, call in enumerate(calls)
            if index not in boundary_writes
            and not self.tools.metadata(call.name, call.arguments).read_only
        }
        return frozenset(other_mutations)

    def _observe_v2(self, state, node_id, event, changed_tools=()):
        controller = self.parallel_controller_v2
        if controller.mode == "off" or self.depth != 0 or not self.allow_initial_subtasks:
            return node_id
        if state.pending_parallel_offer is not None:
            return node_id
        relevant = controller.config.relevant_tools
        if event == "tool_results" and relevant and not set(relevant).intersection(changed_tools):
            return node_id
        observations = _tool_observations(state.messages)
        nodes = tuple({k: n.get(k) for k in ("id", "kind", "scope_id", "status")}
                      for n in self.dag.snapshot()["nodes"]
                      if n["kind"] in {"subtask", "join", "artifact"}
                      # Tool-batch replay joins change every turn even when facts do not.
                      and "ordered_call_ids" not in n.get("metadata", {}))
        frontier_memory = {}
        if self.execution_state_observer is not None:
            frontier_memory = self.execution_state_observer.cache.snapshot(
                self.scope_id
            ).to_dict()
        classifier_memory = getattr(self, "_v2_classifier_state_memory", None)
        if classifier_memory is None:
            classifier_memory = RuntimeClassifierState()
            self._v2_classifier_state_memory = classifier_memory
        classifier_memory.merge_observations(observations, state.step)
        if self._guard_serial_selfcheck(state):
            # Accumulate real evidence, but never evaluate a stale frontier or
            # call the predictor during serial self-check/local repair.
            return node_id
        frontier_memory["verified_classifier_state"] = classifier_memory.snapshot(state.task)
        context = DecisionContextV2(
            run_id=state.run_id, task_id=state.task_id, scope_id=self.scope_id,
            node_id=node_id, step=state.step, event=event, task=state.task,
            observations=tuple(copy.deepcopy(observations)), dag_nodes=nodes,
            tool_names=tuple(sorted(self.tools.names)), expansions=state.plan_expansion_count,
            remaining_expansions=min(self.max_plan_expansions - state.plan_expansion_count,
                                     controller.config.max_expansions - state.v2_expansion_count),
            maximum_width=min(self.max_subtasks, self.max_parallelism),
            allowed_validator_refs=tuple(self.validation_registry.registered_refs()),
            frontier_memory=frontier_memory,
            pending_offer=state.pending_v2_offer is not None)
        evidence_digest = self._v2_verified_evidence_digest(context)
        if (state.pending_v2_offer is not None
                and evidence_digest == state.v2_pending_evidence_digest):
            self.tracer.emit(
                "parallel_v2_request_boundary", request_step=state.step + 1,
                completed_step=state.step, fact_digest=state.v2_last_fact_digest,
                evidence_digest=evidence_digest, facts_changed=False,
                pending_offer=True, observation_count=len(observations),
                reason="pending_offer_no_new_verified_evidence",
            )
            return node_id
        digest = self._v2_fact_digest(context)
        changed = digest != state.v2_last_fact_digest
        self.tracer.emit("parallel_v2_request_boundary", request_step=state.step + 1,
                         completed_step=state.step, fact_digest=digest,
                         evidence_digest=evidence_digest,
                         facts_changed=changed, pending_offer=state.pending_v2_offer is not None,
                         observation_count=len(observations),
                         reason="new_facts" if changed else "unchanged_facts")
        if not changed:
            return node_id
        state.v2_last_fact_digest = digest
        context = replace(context, fact_digest=digest)
        previous = state.pending_v2_offer
        dynamic_frontier = (
            context.frontier_memory.get("verified_classifier_state", {})
            .get("dynamic_frontier", {})
        )
        safe_width = int(dynamic_frontier.get("safe_width") or 0)
        if safe_width < 2:
            evaluation = {
                "schema_version": "semserve.parallel-control.v2",
                "mode": controller.mode,
                "reason": "runtime_frontier_width_below_two",
                "frontier_version": dynamic_frontier.get("frontier_version"),
                "safe_width": safe_width,
                "ready_candidate_ids": [
                    item.get("id")
                    for item in dynamic_frontier.get("ready_candidates", [])
                ],
            }
            self.tracer.emit(
                "parallel_v2_frontier_filtered",
                context=context.to_dict(),
                classifier_input=project_context(context).to_dict(),
                **evaluation,
            )
            if previous is not None:
                self._v2_close_offer(
                    state, "invalidated_by_new_facts:runtime_frontier_width_below_two"
                )
            return node_id
        offer, evaluation = controller.evaluate(context, pending_offer=previous)
        self.tracer.emit("parallel_v2_evaluated", context=context.to_dict(),
                         classifier_input=project_context(context).to_dict(), **evaluation)
        if offer is None:
            if previous is not None:
                self._v2_close_offer(state, "invalidated_by_new_facts:" + evaluation["reason"])
            return node_id
        if previous is not None and offer.offer_id == previous.offer_id:
            old_prompt = controller.prompt(previous)
            state.messages[:] = [m for m in state.messages if not
                (m.get("role") == "user" and m.get("content") == old_prompt)]
            if state.v2_offer_history_cut is None:
                state.v2_offer_history_cut = len(state.messages)
            state.pending_v2_offer = offer
            state.v2_pending_evidence_digest = evidence_digest
            state.messages.append({"role": "user", "content": controller.prompt(offer)})
            self.tracer.emit("parallel_v2_offer_refreshed", step=state.step,
                             offer_id=offer.offer_id, fact_digest=digest,
                             previous_fingerprint=previous.context_fingerprint)
            return node_id
        offer_node = self.dag.add_node(kind="parallel_offer_v2", label="v2 semantic offer",
            scope_id=self.scope_id, status="pending", input=asdict(offer))
        self.dag.add_edge(node_id, offer_node, kind="control")
        self.dag.transition(offer_node, "running")
        self.dag.transition(offer_node, "succeeded", output={"offer_id": offer.offer_id})
        state.pending_v2_offer = offer
        state.v2_offer_history_cut = len(state.messages)
        state.v2_pending_evidence_digest = evidence_digest
        state.v2_decision_repairs = 0
        state.messages.append({"role": "user", "content": controller.prompt(offer)})
        return offer_node

    def _v2_intercept_turn(self, state, turn):
        """Enforce the v4 experiment's one-turn structured offer response."""
        self._v2_expire_offer(state)
        offer = state.pending_v2_offer
        if offer is not None and (len(turn.tool_calls) != 1 or turn.tool_calls[0].name != V2_TOOL):
            state.v2_decision_repairs += 1
            self.tracer.emit("parallel_v2_offer_response_rejected", step=state.step,
                             offer_id=offer.offer_id,
                             tools=[c.name for c in turn.tool_calls],
                             repair=state.v2_decision_repairs)
            if state.v2_decision_repairs >= 2:
                self._v2_close_offer(state, "model_did_not_return_required_v2_decision")
                state.messages.append({"role": "user", "content":
                    "The pending Runtime offer has been closed safely after two invalid responses. "
                    "Continue the original task without assuming that branches were created."})
            else:
                forced = os.environ.get("AGENT_RUNTIME_OFFER_RESPONSE_POLICY") == "forced_parallel"
                rule = (
                    "with mode=parallel and a nonempty dependency-correct plan"
                    if forced else
                    "with mode=parallel and a nonempty dependency-correct plan, or with "
                    "mode=serial/decline, a nonempty reason, and no plan"
                )
                state.messages.append({"role": "user", "content":
                    "Respond to the pending Runtime offer using exactly one choose_execution_mode_v2 "
                    f"function call {rule}. Copy the exact offer_id from the pending offer. "
                    "Never return an empty subtask list. Do not answer "
                    "the task or call another tool in this turn."})
            return True
        return False

    def _v2_close_offer(self, state, outcome):
        offer = state.pending_v2_offer
        if offer is not None:
            self.parallel_controller_v2.close(offer)
            prompt = self.parallel_controller_v2.prompt(offer)
            state.messages[:] = [m for m in state.messages if not
                (m.get("role") == "user" and m.get("content") == prompt)]
            state.pending_v2_offer = None
            state.v2_offer_history_cut = None
            state.v2_pending_evidence_digest = ""
            state.v2_decision_repairs = 0
            self.tracer.emit("parallel_v2_offer_closed", step=state.step,
                             offer_id=offer.offer_id, outcome=outcome)

    def _v2_expire_offer(self, state):
        offer = state.pending_v2_offer
        if offer is not None and state.step > offer.expires_after_step:
            self._v2_close_offer(state, "expired_without_explicit_decision")

    def _execute_v2_decision(self, state, call, node_id):
        offer = state.pending_v2_offer
        offer_history_cut = state.v2_offer_history_cut
        controller = self.parallel_controller_v2
        try:
            if controller.mode != "active" or offer is None or not self.allow_initial_subtasks:
                raise InvalidTaskPlan("no active v2 offer")
            if isinstance(call.arguments, dict) and call.arguments.get("mode") in {"decline", "serial"}:
                controller.decline(call.arguments, offer, state.step)
                state.pending_v2_offer = None
                state.v2_offer_history_cut = None
                state.v2_pending_evidence_digest = ""
                state.v2_decision_repairs = 0
                result = {"ok": True, "execution_mode": "serial", "declined": True,
                          "offer_id": offer.offer_id, "reason": call.arguments["reason"]}
                self.tracer.emit("parallel_v2_offer_declined", **result)
                self.dag.transition(node_id, "succeeded", output=result)
                return result, "succeeded", node_id
            if (state.plan_expansion_count >= self.max_plan_expansions
                    or state.v2_expansion_count >= controller.config.max_expansions):
                raise InvalidTaskPlan("v2 expansion budget exhausted")
            plan, mapping = controller.parse(call.arguments, offer, state.step, self.max_subtasks)
            for ref in plan.acceptance_policy.validators:
                self.validation_registry.resolve(ref)
        except (InvalidTaskPlan, ValueError) as exc:
            state.v2_decision_repairs += 1
            closed = (offer is None or state.step > offer.expires_after_step
                      or state.v2_decision_repairs >= 2)
            if closed and offer is not None:
                controller.close(offer)
                state.pending_v2_offer = None
                state.v2_offer_history_cut = None
                state.v2_pending_evidence_digest = ""
            result = {"ok": False, "v2_protocol_error": True, "error": str(exc),
                      "offer_closed": closed, "fallback_serial": closed}
            self.tracer.emit("parallel_v2_plan_rejected", **result)
            self.dag.transition(node_id, "failed", output=result)
            return result, "failed", node_id
        state.pending_v2_offer = None
        state.v2_offer_history_cut = None
        state.v2_pending_evidence_digest = ""
        state.v2_decision_repairs = 0
        self.tracer.emit("parallel_v2_offer_accepted", offer_id=offer.offer_id,
                         explicit_decision=True, tool=V2_TOOL)
        # Count before dispatch, including failed executions; never auto-replay a plan.
        state.v2_expansion_count += 1
        state.plan_expansion_count += 1
        result, status, terminal = self._run_task_plan(
            state,
            plan,
            node_id,
            history_cut=offer_history_cut,
            checkpoint_source="v2_offer",
        )
        result = {**result, "execution_mode": "parallel_v2", "offer_id": offer.offer_id,
                  "logical_to_runtime_ids": mapping}
        self.dag.transition(node_id, status, output=result)
        self.tracer.emit("parallel_v2_plan_completed", task_id=state.task_id,
                         offer_id=offer.offer_id, status=status, expansion=state.v2_expansion_count)
        return result, status, terminal

    def _v2_attach_frontier_validation(self, state, calls, frontier):
        """Complete the existing report receipt, without another model turn.

        Phase-only receipts need no candidate feedback. Validation feedback stays
        in authoritative history; an explicit next action requires a fresh turn.
        """
        for call in calls:
            if call.name != "report_frontier_state" or not (
                call.arguments.get("ready_upsert") or call.arguments.get("ready_remove")
            ):
                continue
            feedback = {
                "schema_version": "semserve.frontier-validation-feedback.v1",
                "generation": state.v2_frontier_committed_generation,
                "frontier_version": frontier.get("frontier_version"),
                "safe_width": int(frontier.get("safe_width") or 0),
                "validated_ready_ids": [c["id"] for c in frontier.get("ready_candidates", [])],
                "safe_candidate_ids": list(frontier.get("safe_candidate_ids") or []),
                "rejected": [
                    {"id": c["id"], "validation_errors": c.get("validation_errors", []),
                     "read_set": c.get("read_set", []),
                     **({"missing_read_evidence_paths": c["missing_read_evidence_paths"]}
                        if c.get("missing_read_evidence_paths") else {})}
                    for c in frontier.get("advisory_candidates", [])
                ],
                "blocked": [
                    {"id": c["id"], "inferred_needs": c.get("inferred_needs", [])}
                    for c in frontier.get("blocked_candidates", [])
                ],
                "removed_ids": [canonical_work_unit_id(v) for v in call.arguments.get("ready_remove", [])],
            }
            if any(c.get("missing_read_evidence_paths") for c in feedback["rejected"]):
                feedback["next_business_action"] = (
                    "For still-needed candidates, inspect the listed missing_read_evidence_paths "
                    "with read_file on each exact path. A directory listing or variable shell loop "
                    "does not verify per-file contents. Continue with the exposed business tools."
                )
            for message in reversed(state.messages):
                if message.get("role") != "tool" or message.get("tool_call_id") != call.id:
                    continue
                receipt = json.loads(message["content"])
                receipt["runtime_frontier_validation"] = feedback
                message["content"] = json.dumps(receipt, ensure_ascii=False)
                self.tracer.emit(
                    "parallel_v2_frontier_validation_feedback", step=state.step,
                    scope_id=self.scope_id, tool_call_id=call.id, feedback=feedback,
                )
                break

    def _v2_after_tools(self, state, calls, results, node_id):
        autonomous = any(c.name == SPAWN_SUBTASKS_TOOL_NAME and "subtasks" in r
                         for c, r in zip(calls, results))
        if autonomous and state.pending_v2_offer is not None:
            # Temporal association is not proof of explicit offer acceptance.
            self._v2_close_offer(state, "autonomous_spawn_after_offer")
        joined = any(call.name in {SPAWN_SUBTASKS_TOOL_NAME, V2_TOOL}
                     and result.get("execution_mode") == "parallel_v2"
                     for call, result in zip(calls, results))
        # Autonomous spawn results also expose subtasks; preserve their existing path.
        joined = joined or any(call.name == SPAWN_SUBTASKS_TOOL_NAME and "subtasks" in result
                               for call, result in zip(calls, results))
        if joined and self.depth == 0:
            delivered_paths = sorted({
                path
                for result in results
                for path in self._v2_verified_join_materialized_paths(result)
            })
            implementation_paths = [
                path for path in delivered_paths
                if not path.startswith(".semserve/frontier/")
            ]
            self._v2_activate_root_integration_checkpoint(
                state,
                implementation_paths,
                source="live_join",
            )
        report_succeeded = any(
            call.name == "report_frontier_state" and _result_ok(result)
            for call, result in zip(calls, results)
        )
        if report_succeeded and state.v2_frontier_handshake_pending:
            generation = state.v2_frontier_handshake_generation
            reason = state.v2_frontier_handshake_reason
            state.v2_frontier_handshake_pending = False
            state.v2_frontier_handshake_reason = ""
            state.v2_frontier_committed_generation = generation
            # Keep the trained classifier event vocabulary stable.  Commit is
            # transport/control metadata; the semantic event remains a join or
            # an ordinary tool-result boundary.
            commit_event = (
                "join_completed"
                if reason == "root_semantic_join_committed"
                else "tool_results"
            )
            state.v2_next_event = commit_event
            committed_node = self._observe_v2(
                state,
                node_id,
                commit_event,
                changed_tools=("report_frontier_state",),
            )
            memory = getattr(self, "_v2_classifier_state_memory", None)
            frontier = (
                memory.snapshot(state.task).get("dynamic_frontier", {})
                if memory is not None else {}
            )
            if contract_heuristics_enabled():
                inventory = self._g1_discovery_inventory(state)
                self._g1_discovery_checkpoint().notice_report(inventory)
                self.tracer.emit(
                    "g1_discovery_report_committed", scope_id=self.scope_id,
                    step=state.step, generation=generation,
                    evidence_digest=inventory["evidence_digest"],
                    interface_count=inventory["interface_count"],
                    safe_width=int(frontier.get("safe_width") or 0))
            if reason == "root_semantic_join_committed":
                self._v2_arm_post_join_watch(state, frontier)
            self._v2_attach_frontier_validation(state, calls, frontier)
            self.tracer.emit(
                "parallel_v2_frontier_report_committed",
                step=state.step,
                task_id=state.task_id,
                scope_id=self.scope_id,
                generation=generation,
                reason=reason,
                frontier_version=frontier.get("frontier_version"),
                fact_digest=state.v2_last_fact_digest,
                safe_width=int(frontier.get("safe_width") or 0),
                pending_offer=state.pending_v2_offer is not None,
            )
            return committed_node

        successful_write_signatures = self._v2_successful_write_signatures(calls, results)
        successful_write_paths = set(successful_write_signatures)
        if (
            state.v2_post_join_followup_available
            and set(state.v2_post_join_watch_paths).intersection(successful_write_paths)
        ):
            state.v2_post_join_followup_available = False
            state.v2_post_join_watch_paths = ()
            self._v2_schedule_frontier_handshake(
                state, "post_join_watched_output_materialized"
            )
        elif joined:
            self._v2_schedule_frontier_handshake(
                state, "root_semantic_join_committed"
            )
        else:
            evidence_signature = self._v2_successful_evidence_batch_signature(
                calls, results
            )
            if (
                evidence_signature
                and evidence_signature
                not in state.v2_frontier_seen_evidence_signatures
            ):
                state.v2_frontier_seen_evidence_signatures.add(evidence_signature)
                scheduled = self._v2_schedule_frontier_handshake(
                    state, "verified_tool_batch_changed"
                )
                self.tracer.emit(
                    "parallel_v2_generic_evidence_boundary",
                    step=state.step,
                    task_id=state.task_id,
                    scope_id=self.scope_id,
                    evidence_signature=evidence_signature,
                    changed_tools=[
                        call.name
                        for call, result in zip(calls, results)
                        if _result_ok(result)
                    ],
                    handshake_scheduled=scheduled,
                )
        changed = tuple(c.name for c in calls if c.name != V2_TOOL)
        if not joined and not changed:
            return node_id
        state.v2_next_event = "join_completed" if joined else "tool_results"
        return node_id

    def _v2_activate_root_integration_checkpoint(
        self,
        state,
        implementation_paths,
        *,
        source,
    ):
        """Enter the bounded root-integration phase after verified branch join."""

        paths = sorted({
            str(path).removeprefix("/workspace/")
            for path in implementation_paths
            if isinstance(path, str)
            and path
            and not path.removeprefix("/workspace/").startswith(
                ".semserve/frontier/"
            )
        })
        if (
            self.depth != 0
            or not paths
            or self._root_integration_checkpoint_active
        ):
            return False
        self._root_integration_checkpoint_active = True
        self._root_post_join_source_evidence_calls = 0
        self._root_post_join_target_inspection_calls = 0
        rendered_paths = json.dumps(paths[:24], ensure_ascii=False)
        checkpoint_prefix = "Runtime integration checkpoint:"
        if not any(
            message.get("role") == "user"
            and str(message.get("content") or "").startswith(checkpoint_prefix)
            for message in state.messages
            if isinstance(message, dict)
        ):
            state.messages.append({
                "role": "user",
                "content": (
                    f"{checkpoint_prefix} the implementation branches have joined "
                    "with file-integrity-verified deliveries at these workspace-relative "
                    f"paths: {rendered_paths}. Treat these files and the bounded frontier "
                    "reports as the completed branch handoff. Do not restart broad "
                    "legacy-source discovery. Continue serially: inspect the delivered "
                    "target files only as needed, immediately materialize any remaining "
                    "root-owned entrypoint, packaging, or metadata artifacts explicitly "
                    "required by the original task or contract, run focused "
                    "integration/startup checks, and then finish."
                ),
            })
        event = (
            "root_integration_checkpoint_restored"
            if source == "resume"
            else "root_integration_checkpoint_activated"
        )
        self.tracer.emit(
            event,
            task_id=state.task_id,
            step=state.step,
            delivered_paths=paths[:24],
            source=source,
            source_recovery_budget=self._root_post_join_source_evidence_budget,
            target_inspection_budget=(
                self._root_post_join_target_inspection_budget
            ),
        )
        return True

    def _v2_restore_root_integration_checkpoint(self, state):
        """Restore the post-join phase from protocol-complete resume messages."""

        if self.depth != 0 or not state.messages:
            return False
        delivered_paths = []
        for message in state.messages:
            if not isinstance(message, dict) or message.get("role") != "tool":
                continue
            if message.get("name") not in {SPAWN_SUBTASKS_TOOL_NAME, V2_TOOL}:
                continue
            content = message.get("content")
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    continue
            delivered_paths.extend(
                self._v2_verified_join_materialized_paths(content)
            )
        return self._v2_activate_root_integration_checkpoint(
            state,
            delivered_paths,
            source="resume",
        )

    @staticmethod
    def _v2_verified_join_materialized_paths(result):
        """Return only Runtime-attested files from a joined plan result."""

        if not isinstance(result, dict):
            return ()
        values = []
        for key in ("subtasks", "artifacts"):
            rows = result.get(key)
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                artifact = row.get("artifact")
                artifact = artifact if isinstance(artifact, dict) else row
                if artifact.get("delivery_verified") is not True:
                    continue
                materialized = artifact.get("materialized_files")
                if not isinstance(materialized, dict):
                    continue
                for raw_path in materialized:
                    path = str(raw_path or "").replace("\\", "/")
                    while path.startswith("./"):
                        path = path[2:]
                    path = path.removeprefix("/workspace/").lstrip("/")
                    if path:
                        values.append(path)
        return tuple(dict.fromkeys(values))
