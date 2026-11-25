"""Opt-in model-only speculation across a frontier handshake.

Only the coordinator may append messages, commit DAG nodes or execute tools.
Workers receive detached state and an independent, inference-only provider.
The existing handshake, predictor, Offer and tool authorization remain primary.
"""
from __future__ import annotations

import copy
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field, fields
import hashlib
import json
import math
import re
import threading
import time
import uuid
from typing import Any

from .providers.openai_compat import OpenAICompatibleProvider
from .semantics import build_routing_context
from .types import ModelTurn, RuntimeState

ARRAYS = ('done_add','ready_upsert','ready_remove','blocked_add','active_add','active_remove')
CONTROL_TOOLS = frozenset({'report_frontier_state','spawn_subtasks','choose_execution_mode','choose_execution_mode_v2','finish_task','report_blocked'})
# These fields are allowed to advance through the authoritative report commit.
# Budgets, repair modes, failure counters, user task and branch contracts are NOT.
TRANSPORT_FIELDS = frozenset({'messages','step','usage','inference_request_id',
    'last_selected_model','v2_frontier_handshake_pending','v2_frontier_handshake_reason',
    'v2_frontier_committed_generation','v2_last_fact_digest','v2_next_event'})


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,default=str,separators=(',',':')).encode()).hexdigest()


def protocol_complete(messages):
    """Reject unclosed, duplicate or mispaired tool-call groups."""
    pending={}; seen=set()
    for m in messages:
        if m.get('role')=='tool':
            cid=m.get('tool_call_id')
            if cid not in pending or m.get('name',pending[cid])!=pending[cid]:return False
            del pending[cid]
        else:
            if pending:return False
            for call in m.get('tool_calls') or []:
                cid=call.get('id');fn=call.get('function') or {}
                if not cid or cid in seen or not fn.get('name'):return False
                seen.add(cid);pending[cid]=fn['name']
    return not pending


def reported_phase(messages):
    phase='inspect'
    for m in messages:
        if m.get('role')!='tool' or m.get('name')!='report_frontier_state':continue
        try:r=json.loads(m['content'])
        except (ValueError,TypeError,KeyError):continue
        if r.get('ok') is True and isinstance(r.get('delta'),dict):phase=r['delta'].get('phase',phase)
    return phase


def schema_accepts(value, schema):
    """Conservative local subset. Unsupported constraints invalidate reuse.

    The ordinary Runtime/tool validators still run after this gate. This gate
    never relaxes a schema, and adds no third-party dependency to the snapshot.
    """
    supported={'type','properties','required','additionalProperties','items','minItems','maxItems',
        'uniqueItems','enum','const','minLength','maxLength','pattern','minimum','maximum',
        'exclusiveMinimum','exclusiveMaximum','description','title','default'}
    if not isinstance(schema,dict) or set(schema)-supported:return False
    kind=schema.get('type')
    if isinstance(kind,list):return any(schema_accepts(value,{**schema,'type':k}) for k in kind)
    types={'object':lambda v:isinstance(v,dict),'array':lambda v:isinstance(v,list),
        'string':lambda v:isinstance(v,str),'boolean':lambda v:type(v) is bool,
        'integer':lambda v:type(v) is int,'number':lambda v:type(v) in (int,float),'null':lambda v:v is None}
    if kind is not None and (kind not in types or not types[kind](value)):return False
    if 'enum' in schema and value not in schema['enum']:return False
    if 'const' in schema and value!=schema['const']:return False
    if isinstance(value,dict):
        if any(k not in value for k in schema.get('required',[])):return False
        props=schema.get('properties',{})
        for k,v in value.items():
            if k in props:
                if not schema_accepts(v,props[k]):return False
            elif schema.get('additionalProperties') is False:return False
            elif isinstance(schema.get('additionalProperties'),dict) and not schema_accepts(v,schema['additionalProperties']):return False
    if isinstance(value,list):
        if len(value)<schema.get('minItems',0) or len(value)>schema.get('maxItems',float('inf')):return False
        if schema.get('uniqueItems') and len({digest(v) for v in value})!=len(value):return False
        if 'items' in schema and any(not schema_accepts(v,schema['items']) for v in value):return False
    if isinstance(value,str):
        if len(value)<schema.get('minLength',0) or len(value)>schema.get('maxLength',float('inf')):return False
        if 'pattern' in schema and re.search(schema['pattern'],value) is None:return False
    if type(value) in (int,float):
        if value<schema.get('minimum',float('-inf')) or value>schema.get('maximum',float('inf')):return False
        if 'exclusiveMinimum' in schema and value<=schema['exclusiveMinimum']:return False
        if 'exclusiveMaximum' in schema and value>=schema['exclusiveMaximum']:return False
    return True


@dataclass
class SpeculativeGeneration:
    id: str
    generation: int
    handshake_step: int
    prefix: list[dict]
    phase: str
    state_digest: str
    schemas: list[dict]
    routing: dict
    provider: Any
    request_id: str
    session_id: str
    future: Future | None = None
    started: float = 0.0
    ended: float = 0.0
    usage: dict = field(default_factory=dict)
    error_type: str = ''
    disposition: str = 'pending'
    reason: str = ''
    authorized_state_digest: str = ''
    authorized_messages_digest: str = ''
    authorized_progress_version: int = 0
    lock: threading.RLock = field(default_factory=threading.RLock)


class HandshakeSpeculationMixin:
    def _hs_init(self, enabled, wait_seconds, provider_factory, commit_observer):
        if not math.isfinite(wait_seconds) or wait_seconds<=0:raise ValueError('handshake_speculation_wait_seconds must be finite and positive')
        self.handshake_speculation_enabled=bool(enabled)
        self.handshake_speculation_wait_seconds=float(wait_seconds)
        self.handshake_speculation_provider_factory=provider_factory
        self.handshake_speculation_commit_observer=commit_observer
        self._hs_ticket=None; self._hs_pool=None; self._hs_generations=[]

    def _hs_emit(self,event,ticket=None,**data):
        if ticket is not None:data.update(generation_id=ticket.id,handshake_generation=ticket.generation,
            speculative_request_id=ticket.request_id,speculative_session_id=ticket.session_id)
        self.tracer.emit('handshake_speculation_'+event,scope_id=self.scope_id,**data)

    def _hs_state_digest(self,state):
        state_fields={f.name:getattr(state,f.name) for f in fields(state) if f.name not in TRANSPORT_FIELDS}
        runtime_fields={name:getattr(self,name) for name in (
            'allowed_input_refs','branch_inputs','required_artifact_kinds','required_artifact_paths',
            'required_test_targets','require_file_branch_contract','max_parallelism','max_subtasks',
            'max_subtask_depth','max_plan_expansions','max_initial_plan_expansions',
            'max_recovery_plan_expansions','max_plan_validation_failures','allow_initial_subtasks',
            'allow_recovery_subtasks','fork_only_stable_prefix')}
        runtime_fields['allowed_tools']=sorted(self.policy.allowed_tools)
        runtime_fields['controller_mode']=self.parallel_controller_v2.mode
        runtime_fields['controller_config']=str(self.parallel_controller_v2.config)
        runtime_fields['recovery_generation']=self._recovery.generation
        feedback = self._vp_current_root_feedback()
        if feedback is not None:
            runtime_fields['root_recovery_feedback'] = feedback
        return digest([state_fields,runtime_fields])

    def _hs_business_preview(self,state):
        # _model_tool_schemas has coordinator side effects. Use a shallow Runtime
        # view plus detached mutable envelope, never toggle the live pending flag.
        shadow=copy.copy(self)
        shadow._fork_parent_tool_schemas=copy.deepcopy(self._fork_parent_tool_schemas)
        shadow._frontier_report_request_active=False
        preview=copy.deepcopy(state);preview.v2_frontier_handshake_pending=False
        preview.v2_frontier_handshake_reason='';preview.step+=1
        schemas=copy.deepcopy(shadow._model_tool_schemas(preview))
        return preview,schemas,build_routing_context(preview,tools_available=bool(schemas))

    def _hs_new_provider(self):
        factory=self.handshake_speculation_provider_factory
        primary_inference_only=(type(self.provider) is OpenAICompatibleProvider
            or type(self.provider).__dict__.get('speculation_inference_only',False))
        if not primary_inference_only and self.handshake_speculation_commit_observer is None:
            return None
        if factory is None:
            # Legacy CaptureProvider.complete also commits summary captures.
            # Subclasses are not implicitly inference-only just by inheriting.
            if (type(self.provider) is not OpenAICompatibleProvider
                    and not type(self.provider).__dict__.get('speculation_inference_only',False)):
                return None
            p=self.provider.fork(stream=False)
        else:p=factory()
        if p is self.provider:return None
        if type(p) is not OpenAICompatibleProvider and not type(p).__dict__.get('speculation_inference_only',False):return None
        return p

    def _hs_prepare(self,state):
        self._recovery_require_open()
        if self._guard_serial_selfcheck(state):return
        if (not self.handshake_speculation_enabled or self.depth!=0 or self._hs_ticket is not None
                or not state.v2_frontier_handshake_pending or state.pending_v2_offer is not None
                or state.pending_parallel_offer is not None or state.tool_repair_mode
                or state.status!='running' or state.reasoning_mode!='off'
                or self._cancel_event.is_set()
                or state.step>=self.max_steps or self.speculation_manager is not None):return
        if any(g.future is not None and not g.future.done() for g in self._hs_generations):
            self._hs_emit('not_started',reason='previous_discarded_request_still_running');return
        # A malformed report retry must not create a new speculative request on
        # top of the earlier report-only instruction/unclosed call group.
        if not protocol_complete(state.messages):
            self._hs_emit('not_started',reason='unbalanced_parent_protocol');return
        if state.messages and state.messages[-1].get('role')=='user' and (
                str(state.messages[-1].get('content','')).startswith('Runtime requires one bounded semantic commit')
                or str(state.messages[-1].get('content','')).startswith('Before continuing, call report_frontier_state')):
            self._hs_emit('not_started',reason='report_retry');return
        try:
            preview,schemas,routing=self._hs_business_preview(state)
            provider=self._hs_new_provider()
            if provider is None:
                self._hs_emit('not_started',reason='no_independent_inference_only_provider');return
        except Exception as exc:
            self._hs_emit('not_started',reason='snapshot_or_provider_error',error_type=type(exc).__name__);return
        gid=uuid.uuid4().hex
        preview.inference_request_id=f'{state.inference_request_id}-spec-{gid}'
        preview.inference_session_id=f'{state.inference_session_id}-spec-{gid}'
        preview.gateway_routing_key=preview.inference_session_id
        ticket=SpeculativeGeneration(gid,state.v2_frontier_handshake_generation,state.step,
            copy.deepcopy(state.messages),reported_phase(state.messages),self._hs_state_digest(state),
            schemas,routing.to_dict(),provider,preview.inference_request_id,preview.inference_session_id)
        if self._hs_pool is None:self._hs_pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='handshake-model-only')
        self._hs_ticket=ticket;self._hs_generations.append(ticket)
        self._hs_emit('started',ticket,snapshot_digest=digest(ticket.prefix),tool_names=[s['function']['name'] for s in schemas])
        request = self._vp_business_request(preview)
        ticket.future=self._hs_pool.submit(self._hs_generate,ticket,request,copy.deepcopy(schemas),copy.deepcopy(routing))

    def _hs_generate(self,ticket,state,schemas,routing):
        with ticket.lock:ticket.started=time.time()
        try:
            turn=ticket.provider.complete(state,schemas,routing)
            with ticket.lock:ticket.usage=copy.deepcopy(getattr(turn,'usage',{}) or {})
            return turn
        except BaseException as exc:
            with ticket.lock:ticket.error_type=type(exc).__name__
            raise
        finally:
            with ticket.lock:ticket.ended=time.time()
            self._hs_emit('response',ticket,started=ticket.started,ended=ticket.ended,
                usage=ticket.usage,error_type=ticket.error_type,disposition=ticket.disposition)

    def _hs_discard(self,reason):
        ticket=self._hs_ticket
        if ticket is None:return
        with ticket.lock:ticket.disposition='discarded';ticket.reason=reason
        cancelled=ticket.future.cancel() if ticket.future is not None else False
        self._hs_ticket=None
        self._hs_emit('discarded',ticket,reason=reason,local_future_cancelled=cancelled,
            remote_abort_confirmed=False)

    def _hs_after_tools(self,state,calls):
        ticket=self._hs_ticket
        if ticket is None or ticket.disposition!='pending':return
        if len(calls)!=1 or calls[0].name!='report_frontier_state':
            self._hs_discard('not_a_report_only_turn');return
        if (state.v2_frontier_handshake_pending
                or state.v2_frontier_committed_generation!=ticket.generation
                or state.v2_frontier_handshake_generation!=ticket.generation):
            self._hs_discard('report_not_committed');return
        # An actual Offer supersedes the speculative business turn. Advisory
        # progress in a committed report does not supersede it by itself.
        if state.pending_v2_offer is not None or state.pending_parallel_offer is not None:
            self._hs_discard('offer_pending');return
        tail=state.messages[len(ticket.prefix):]
        if state.messages[:len(ticket.prefix)]!=ticket.prefix or len(tail)!=3:
            self._hs_discard('authoritative_history_changed');return
        if (tail[0].get('role')!='user' or tail[1].get('role')!='assistant'
                or tail[2].get('role')!='tool' or tail[2].get('tool_call_id')!=calls[0].id):
            self._hs_discard('report_protocol_mismatch');return
        if tail[1].get('content'):
            self._hs_discard('report_extra_narrative');return
        try:result=json.loads(tail[2]['content']);delta=result['delta']
        except (ValueError,TypeError,KeyError):
            self._hs_discard('invalid_report_receipt');return
        required=set(ARRAYS)|{'phase'}
        if (result.get('ok') is not True or not isinstance(delta,dict)
                or not required.issubset(delta) or set(delta)-required-{'schema_version'}
                or any(not isinstance(delta[key],list) for key in ARRAYS)
                or delta.get('schema_version','semserve.turn-state-delta.v1')!='semserve.turn-state-delta.v1'):
            self._hs_discard('invalid_report_receipt');return
        if delta['phase']!=ticket.phase:
            self._hs_discard('phase_changed');return
        feedback=result.get('runtime_frontier_validation')
        if isinstance(feedback,dict) and feedback.get('next_business_action'):
            # The shadow was generated before Runtime gave this instruction.
            self._hs_discard('frontier_feedback_requires_business_turn');return
        if self._hs_state_digest(state)!=ticket.state_digest:
            self._hs_discard('control_or_contract_changed');return
        # Recompute only after the real report's normal Runtime commit/prediction.
        preview,schemas,routing=self._hs_business_preview(state)
        if schemas!=ticket.schemas or routing.to_dict()!=ticket.routing:
            self._hs_discard('business_envelope_changed');return
        with ticket.lock:
            ticket.disposition='authorized'
            ticket.authorized_state_digest=self._hs_state_digest(state)
            # Actual schema construction will append the same deterministic
            # business-mode marker as this detached preview. Preserve the exact
            # original three-message report-tail validation above.
            ticket.authorized_messages_digest=digest(preview.messages)
            ticket.authorized_progress_version=self._tool_progress_version
        self._hs_emit('authorized',ticket,report_step=state.step)

    def _hs_validate_turn(self,state,schemas,turn):
        if (not isinstance(turn,ModelTurn) or not isinstance(turn.assistant_message,dict)
                or turn.assistant_message.get('role')!='assistant' or not isinstance(turn.content,str)
                or not isinstance(turn.tool_calls,list) or not isinstance(turn.usage,dict)
                or not isinstance(turn.route_info,dict)):return 'invalid_model_turn'
        if getattr(self,'output_guard_enabled',False):
            from .output_guard import capture_allowed
            if not capture_allowed(turn):return 'output_guard_invalid_narration'
            if not turn.tool_calls:return 'output_guard_unstructured_root_completion'
        if turn.route_info.get('output_budget_exhausted') or turn.route_info.get('finish_reason')=='length':return 'output_truncated'
        if (turn.assistant_message.get('reasoning_content') or turn.usage.get('reasoning_tokens')
                or isinstance(turn.usage.get('completion_tokens_details'),dict)
                and turn.usage['completion_tokens_details'].get('reasoning_tokens')):return 'reasoning_output'
        if turn.route_info.get('requested_reasoning','off')!='off':return 'reasoning_route'
        ids=set();wire=turn.assistant_message.get('tool_calls') or []
        if not isinstance(wire,list):return 'assistant_call_mismatch'
        if len(wire)!=len(turn.tool_calls):return 'assistant_call_mismatch'
        historical_ids={c.get('id') for m in state.messages for c in m.get('tool_calls') or []}
        names={s['function']['name'] for s in schemas}
        parameters={s['function']['name']:s['function'].get('parameters',{}) for s in schemas}
        for call,msg in zip(turn.tool_calls,wire):
            if not isinstance(msg,dict) or not isinstance(msg.get('function'),dict):return 'assistant_call_mismatch'
            if call.name in CONTROL_TOOLS:return 'speculative_control_call'
            if call.id in ids or call.id in historical_ids:return 'duplicate_call_id'
            ids.add(call.id)
            if not isinstance(call.arguments,dict) or self.policy.validate(call) or call.name not in names:return 'unauthorized_tool_call'
            if not schema_accepts(call.arguments,parameters[call.name]):return 'invalid_tool_schema'
            try:args=msg['function']['arguments'];args=json.loads(args) if isinstance(args,str) else args
            except (KeyError,ValueError,TypeError):return 'invalid_call_arguments'
            if msg.get('id')!=call.id or msg['function'].get('name')!=call.name or args!=call.arguments:return 'assistant_call_mismatch'
        if not turn.tool_calls and not turn.content.strip():return 'empty_business_turn'
        if not protocol_complete(state.messages):return 'unbalanced_commit_history'
        return ''

    def _hs_primary_complete(self, state, schemas, routing):
        self._recovery_require_open()
        request = state if self._guard_serial_selfcheck(state) else self._vp_business_request(state)
        turn = self.provider.complete(request, schemas, routing)
        self._recovery_require_open()
        return turn

    def _hs_complete(self,state,schemas,routing):
        self._recovery_require_open()
        self._check_cancelled()
        if self._guard_serial_selfcheck(state):
            self._hs_discard('serial_selfcheck_started')
            return self._hs_primary_complete(state,schemas,routing)
        ticket=self._hs_ticket
        if ticket is None:return self._hs_primary_complete(state,schemas,routing)
        if ticket.disposition=='pending':
            # This is the actual handshake request. Its ordinary path is primary.
            if {s['function']['name'] for s in schemas}=={'report_frontier_state'}:
                return self._hs_primary_complete(state,schemas,routing)
            self._hs_discard('report_protocol_changed')
            return self._hs_primary_complete(state,schemas,routing)
        if (state.step!=ticket.handshake_step+1 or state.v2_frontier_handshake_pending
                or state.pending_v2_offer is not None or state.pending_parallel_offer is not None
                or self._hs_state_digest(state)!=ticket.authorized_state_digest
                or digest(state.messages)!=ticket.authorized_messages_digest
                or self._tool_progress_version!=ticket.authorized_progress_version
                or schemas!=ticket.schemas or routing.to_dict()!=ticket.routing):
            self._hs_discard('stale_before_commit')
            return self._hs_primary_complete(state,schemas,routing)
        deadline=time.monotonic()+self.handshake_speculation_wait_seconds
        try:
            while True:
                self._check_cancelled()
                self._recovery_require_open()
                remaining=deadline-time.monotonic()
                if remaining<=0:
                    self._hs_discard('business_wait_timeout')
                    return self._hs_primary_complete(state,schemas,routing)
                try:turn=ticket.future.result(timeout=min(.025,remaining));break
                except FutureTimeout:
                    if ticket.future.done():
                        self._hs_discard('business_provider_error')
                        return self._hs_primary_complete(state,schemas,routing)
                    continue
        except Exception as exc:
            self._hs_discard('business_provider_error')
            self._check_cancelled()
            return self._hs_primary_complete(state,schemas,routing)
        # No worker may change authoritative state; still recheck at the exact
        # consumption boundary to catch cancellation or coordinator callbacks.
        self._check_cancelled()
        self._recovery_require_open()
        _,fresh_schemas,fresh_routing=self._hs_business_preview(state)
        if (self._hs_state_digest(state)!=ticket.authorized_state_digest
                or digest(state.messages)!=ticket.authorized_messages_digest
                or self._tool_progress_version!=ticket.authorized_progress_version
                or fresh_schemas!=schemas or fresh_routing.to_dict()!=routing.to_dict()):
            self._hs_discard('stale_after_wait');return self._hs_primary_complete(state,schemas,routing)
        reason=self._hs_validate_turn(state,schemas,turn)
        if reason:
            self._hs_discard(reason);return self._hs_primary_complete(state,schemas,routing)
        turn=copy.deepcopy(turn)
        turn.route_info['handshake_speculation']={'generation_id':ticket.id,'request_id':ticket.request_id,
            'session_id':ticket.session_id,'generation_started':ticket.started,'generation_ended':ticket.ended,
            'commit_step':state.step,'snapshot_digest':digest(ticket.prefix)}
        # A capturing executor may need to publish EXECUTION_DELTA_JSON and a
        # logical turn record. Such hooks run ONLY after validation on the main
        # thread. Failure is fatal before tools, never silently replayed.
        if self.handshake_speculation_commit_observer is not None:
            try:self.handshake_speculation_commit_observer(state,turn)
            except BaseException:
                self._hs_discard('commit_observer_failed');raise
        self._recovery_require_open()
        with ticket.lock:ticket.disposition='committed'
        self._hs_ticket=None
        self._hs_emit('committed',ticket,commit_step=state.step,usage=ticket.usage)
        return turn

    def handshake_speculation_metrics(self):
        """Physical speculative usage is separate; reused usage is in normal usage.

        Total actual usage = normal committed usage + discarded usage. Do not
        add all speculative usage again: that would double-count reused calls.
        """
        result={'submitted':len(self._hs_generations),'committed':0,'discarded':0,'unfinished':0,
                'usage_all_speculative':{},'usage_discarded':{},'errors':0,'completed_without_usage':0}
        for t in self._hs_generations:
            with t.lock:
                if t.disposition in result:result[t.disposition]+=1
                if t.future is None or not t.future.done():result['unfinished']+=1
                elif not t.usage:result['completed_without_usage']+=1
                result['errors']+=bool(t.error_type)
                for k,v in t.usage.items():
                    if not isinstance(v,(int,float)):continue
                    result['usage_all_speculative'][k]=result['usage_all_speculative'].get(k,0)+v
                    if t.disposition=='discarded':result['usage_discarded'][k]=result['usage_discarded'].get(k,0)+v
        return result

    def wait_for_handshake_speculation(self,timeout=5):
        deadline=time.monotonic()+timeout
        for t in self._hs_generations:
            if t.future is not None:
                try:t.future.result(timeout=max(0,deadline-time.monotonic()))
                except FutureTimeout:
                    if not t.future.done():raise
                except Exception:pass
        return self.handshake_speculation_metrics()

    def _hs_shutdown(self):
        self._hs_discard('scope_ended')
        if self._hs_pool is not None:
            self._hs_pool.shutdown(wait=False,cancel_futures=True)
            self._hs_pool=None
