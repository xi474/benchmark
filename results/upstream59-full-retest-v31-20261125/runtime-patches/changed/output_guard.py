"""Opt-in root action/completion protocol; workers remain inference-only."""
from __future__ import annotations

import copy
from contextlib import nullcontext
import json
import re
import time

from .tools.base import ToolExecutionContext

VERSION = 'agent-output-guard-v3-narration-compression'
CONTROL_TOOLS = frozenset({'finish_task', 'report_blocked'})
RUN_TESTS_TOOL = 'run_tests'
SOFT_NARRATIVE_CHARS = 256
HARD_NARRATIVE_CHARS = 1024
MAX_RECOVERIES = 3
MAX_ROOT_CHECKS = 3
SELF_CHECK_PARALLEL_TOOLS = frozenset({
    'report_frontier_state', 'spawn_subtasks',
    'choose_execution_mode', 'choose_execution_mode_v2',
})
SELF_CHECK_SERIAL_PROMPT = (
    '[RUNTIME_SELF_CHECK_SERIAL] Public checks passed and Runtime requires '
    'bounded visible-contract self-checks. Complete the supplied self-check '
    'protocol and any local repairs serially. Frontier handshakes, prediction, '
    'Offers, speculative generation and subagent spawn are suspended in this '
    'phase. Earlier report/Offer instructions are historical and do not '
    'authorize another report or plan. Use the currently exposed file/shell '
    'tools, preserve all check/repair/ownership requirements, and call '
    'finish_task for real validation. These controls do not change the '
    'visible requirements, self-check budgets or hidden-verifier boundary.'
)
PROMPT = '''AGENT OUTPUT AND ROOT COMPLETION PROTOCOL (agent-output-guard-v2)
Both root and child agents must keep ordinary narration within 256 Unicode characters.
Once evidence is sufficient, immediately use tools for the next action. Do not
put extended deliberation, repeated alternatives, or complete code in narration.
Code belongs in file-tool arguments. Valid EXECUTION_DELTA_JSON metadata and
Frontier Report/tool arguments retain their existing independent schemas and
are NOT included in the narration limit. Do not invent completion evidence.
The root must continue by tool calls, or call finish_task with a summary of at
most 1024 characters. Runtime runs the public check.py before accepting finish.
If it fails, fix the reported public failure; do not claim success. Use
report_blocked for a real inability to continue, with a reason <=1024 characters.
ROOT ONLY: public check.py is necessary but not sufficient for completion. Call
finish_task to receive the exact visible-check protocol after public checks pass.
Then prepare .semserve/visible_checks/check.py using standard-library unittest
for high-risk visible requirements, independent expectations/invariants and relevant
boundaries. Run the tests with shell, inspect real tracebacks, and call finish_task
for Runtime to rerun and verify the final code version. Existing SDK tests remain
compatible and retain their pending/frozen-case requirements. Follow the supplied
bounded repair protocol; printed verdicts are not evidence.
Never use hidden verifiers or reference answers.
If completion is deferred, follow its check protocol; distinguish faulty probes
from faulty implementation, fix the responsible code, and request finish again.
finish_task/report_blocked are ROOT-ONLY controls. Child agents keep their
existing focused-check, delivery, file ownership, and completion contracts.
At a report-only handshake call report_frontier_state exactly once. At a pending
Offer use the existing required execution-mode response, including serial/decline.
PUBLIC CHECK FAILURE DISCIPLINE (mandatory): when a public check fails, CONVERGE
in ONE repair cycle instead of patching piecemeal:
1. Run the deliverable entry on public_input.json and save its output.
2. Read public_expected.json and diff your output against it FIELD BY FIELD.
3. Write down the COMPLETE list of mismatches as $.path: expected X got Y.
4. Diagnose the COMMON ROOT CAUSE of the mismatches (one logic bug usually
   explains several fields). Fix the root cause with a SINGLE apply_patch
   (or one write_file for a file you own), then re-run the public check.
5. Repeat only if NEW mismatches remain. If a fix does not reduce the mismatch
   count, STOP patching: re-read the relevant files and re-derive the rules
   from the task description before editing again. Never stack many edits
   without re-running the check; do not call apply_patch more than a few
   times per file between check runs.
FILE EDIT DISCIPLINE:
- apply_patch is for small, targeted edits: exact old_text, minimal new_text.
  Do NOT rewrite an entire module with apply_patch to change a few lines, and do
  NOT repeatedly rewrite the same file; if a rewrite is truly needed, plan it first
  and verify with tests/public checks right after.
- write_file may overwrite only files you created yourself this session or explicit
  placeholder stubs. Every other existing file must be changed with apply_patch.
- Re-read a file before editing if your last read was several steps ago.
- After each edit batch, run the affected test or public check BEFORE making
  further edits; do not stack many unreviewed changes.
'''.strip()


class OutputGuardFailure(RuntimeError):
    pass


def narration(content):
    """Exclude exactly one valid, bounded metadata object; never arbitrary text."""
    content = content or ''
    matches = list(re.finditer(r'EXECUTION_DELTA_JSON:\s*', content))
    if len(matches) != 1:
        return content
    m = matches[0]
    try:
        raw, end = json.JSONDecoder().raw_decode(content[m.end():])
        from .qwen_frontier_predictor import normalize_execution_delta
        allowed = {'phase','done_add','ready_upsert','ready_remove','blocked_add',
                   'active_add','active_remove','schema_version'}
        if (not isinstance(raw,dict) or set(raw)-allowed or end>65536
                or normalize_execution_delta(raw) is None):
            return content
    except (ValueError,TypeError):
        return content
    return content[:m.start()] + content[m.end()+end:]


def capture_allowed(turn):
    return (turn.route_info.get('finish_reason') != 'length'
            and not turn.route_info.get('output_budget_exhausted')
            and (len(narration(turn.content).strip()) <= HARD_NARRATIVE_CHARS
                or (turn.route_info.get('narration_compression_version')=='small-model-narration-v1'
                    and turn.route_info.get('narration_compression_status')=='fallback_original')))


def metadata_capture_allowed(turn, schemas):
    if not capture_allowed(turn) or not turn.tool_calls:
        return False
    if {s['function']['name'] for s in schemas}=={'report_frontier_state'}:
        return len(turn.tool_calls)==1 and turn.tool_calls[0].name=='report_frontier_state'
    for c in turn.tool_calls:
        if c.name == RUN_TESTS_TOOL and (len(turn.tool_calls) != 1 or c.arguments != {}):
            return False
        if c.name in CONTROL_TOOLS:
            field='summary' if c.name=='finish_task' else 'reason'
            value=c.arguments.get(field)
            if len(turn.tool_calls)!=1 or set(c.arguments)!={field} or not isinstance(value,str) or not value.strip() or len(value)>1024:
                return False
    return True


def control_schemas():
    result=[]
    for name, field, desc in (
        ('finish_task','summary','ROOT ONLY. Request task completion. Runtime requires public check.py and bounded independent visible-contract checks; it may defer completion with the required check protocol. Never claim hidden-verifier success.'),
        ('report_blocked','reason','ROOT ONLY. End this attempt as blocked/failed, never as a successful task. State the actual obstacle.'),
    ):
        result.append({'type':'function','function':{'name':name,'description':desc,
            'parameters':{'type':'object','properties':{field:{'type':'string',
                'description':'At most 1024 Unicode characters; concise facts, no code or extended deliberation.',
                'maxLength':1024}},'required':[field],'additionalProperties':False}}})
    return result


def run_tests_schema():
    return {'type':'function','function':{'name':RUN_TESTS_TOOL,
        'description':('ROOT SERIAL SELF-CHECK ONLY. Execute the existing '
            '.semserve/visible_checks/check.py with Runtime-injected helpers and '
            'return structured failures and coverage. Reuses the current review '
            'budget. Correct the reported cause, rerun, then call finish_task '
            'for final public validation. This tool does not complete the task.'),
        'parameters':{'type':'object','properties':{},'required':[],
            'additionalProperties':False}}}


def tool_choice(state, tools, default):
    names={s.get('function',{}).get('name') for s in tools}
    if state.parent_task_id:
        return default
    if names == {'report_frontier_state'}:
        return {'type':'function','function':{'name':'report_frontier_state'}}
    if CONTROL_TOOLS.issubset(names):
        return 'required'
    return default


def deduplicate_completion_instruction(messages, call_id, instruction):
    """Keep the exact next-user instruction once; never shorten evidence.

    Run only after the full instruction was appended. The tool result in the
    DAG/tracer and the validator's original receipt remain immutable.
    """
    if (not isinstance(instruction, str) or not instruction or not call_id
            or not messages or messages[-1].get('role') != 'user'
            or messages[-1].get('content') != instruction):
        return 0
    for message in reversed(messages[:-1]):
        if message.get('role') != 'tool' or message.get('tool_call_id') != call_id:
            continue
        if message.get('name') != 'finish_task':
            return 0
        try:
            original = message['content']
            receipt = json.loads(original)
        except (ValueError, TypeError, KeyError):
            return 0
        if not isinstance(receipt, dict):
            return 0
        check = receipt.get('check')
        if (receipt.get('validation_status') != 'self_check_pending'
                or receipt.get('public_check_passed') is not True
                or not isinstance(check, dict) or check.get('completion_blocked')
                or check.get('completion_instruction') != instruction):
            return 0
        del check['completion_instruction']
        message['content'] = json.dumps(receipt, ensure_ascii=False)
        return len(original) - len(message['content'])
    return 0


class RootOutputGuardMixin:
    def _guard_init(self, enabled, checker):
        self.output_guard_enabled=bool(enabled)
        self.root_public_checker=checker
        self._guard_recoveries=0
        self._guard_check_count=0
        self._selfcheck_deadline=None
        self._selfcheck_deadline_recorded=False
        self._selfcheck_sdk_hint_used=False

    def _guard_serial_selfcheck(self, state):
        return bool(self.output_guard_enabled and self.depth == 0
                    and getattr(state, 'serial_selfcheck', False))

    def _guard_run_tests_available(self, state):
        return (self._guard_serial_selfcheck(state)
                and not state.tool_repair_mode
                and callable(getattr(self.root_public_checker, 'run_tests', None)))

    def _guard_enter_serial_selfcheck(self, state, *, restored=False):
        if not self.output_guard_enabled or self.depth != 0 or state.serial_selfcheck:
            return False
        state.serial_selfcheck = True
        getter=getattr(self.root_public_checker,'selfcheck_deadline',None)
        self._selfcheck_deadline=getter() if callable(getter) else time.monotonic()+300
        # Entry is a completed finish_task boundary, not a partially executed
        # report. Keep history intact and revoke only future parallel control.
        self._hs_discard('visible_contract_completion_required')
        self._v2_close_offer(state, 'serial_selfcheck_started')
        state.pending_parallel_offer = None
        state.pending_parallel_controller = None
        state.deferred_parallel_offer = None
        state.parallel_offer_history_cut = None
        state.v2_frontier_handshake_pending = False
        state.v2_frontier_handshake_reason = ''
        state.v2_post_join_followup_available = False
        state.v2_post_join_watch_paths = ()
        self._report_reset_schema_authorization()
        on_entry = getattr(self, '_e1_enter_selfcheck', None)
        if on_entry is not None:
            on_entry(state)
        self.tracer.emit('selfcheck_serial_started', scope_id=self.scope_id,
            step=state.step, restored=restored,
            disabled=['handshake','predictor','handshake_c4','speculation','spawn'],
            tool_workers=1)
        return True

    def _guard_check_selfcheck_deadline(self, state):
        deadline=getattr(self,'_selfcheck_deadline',None)
        if not self._guard_serial_selfcheck(state) or deadline is None or time.monotonic()<deadline:
            return
        from .selfcheck_deadline import SelfcheckDeadlineExceeded
        if not self._selfcheck_deadline_recorded:
            self._selfcheck_deadline_recorded=True
            record=getattr(self.root_public_checker,'selfcheck_budget_exhausted',None)
            if callable(record):record()
            self.tracer.emit('selfcheck_budget_exhausted',scope_id=self.scope_id,
                step=state.step,completed=False,reason='absolute_review_deadline')
        state.status='failed'
        raise SelfcheckDeadlineExceeded('selfcheck_budget_exhausted: self-check incomplete; public pass remains separate')

    def _guard_selfcheck_deadline_scope(self, state):
        if not self._guard_serial_selfcheck(state):
            return nullcontext()
        self._guard_check_selfcheck_deadline(state)
        from .selfcheck_deadline import deadline_scope
        return deadline_scope(getattr(self,'_selfcheck_deadline',None))

    def _guard_selfcheck_result(self, state, call, result):
        if (not self._guard_serial_selfcheck(state) or call.name!='shell'
                or self._selfcheck_sdk_hint_used):
            return result
        error=str(result.get('output',''))+'\n'+str(result.get('error',''))
        if not re.search(r"ModuleNotFoundError:\s*No module named ['\"]semserve_check['\"]",error):
            return result
        self._selfcheck_sdk_hint_used=True
        instruction=getattr(self.root_public_checker,'selfcheck_instruction','')
        note=('semserve_check exists only inside Runtime execution of the check script. '
              'Do not import it in an ordinary shell or search/install it. Write '
              '.semserve/visible_checks/check.py with the supplied API, then call finish_task.')
        result={**result,'runtime_recovery_instruction':note+('\n'+instruction if instruction else ''),
                'runtime_recovery_kind':'selfcheck_sdk_scope_once'}
        self.tracer.emit('selfcheck_sdk_scope_recovery',scope_id=self.scope_id,
            step=state.step,tool_call_id=call.id,original_error_preserved=True)
        return result

    def _guard_restore_selfcheck_phase(self, state):
        if not self.output_guard_enabled or self.depth != 0:
            return
        pending = False
        calls = {}
        for message in state.messages:
            if message.get('role') == 'assistant':
                for call in message.get('tool_calls') or []:
                    calls[call.get('id')] = call.get('function', {}).get('name')
            if (message.get('role') != 'tool' or message.get('name') != 'finish_task'
                    or calls.pop(message.get('tool_call_id'), None) != 'finish_task'):
                continue
            try:
                receipt = json.loads(message.get('content', ''))
            except (ValueError, TypeError):
                continue
            if not isinstance(receipt, dict):
                continue
            if receipt.get('validation_status') == 'completed':
                pending = False
            elif (receipt.get('validation_status') == 'self_check_pending'
                    and receipt.get('public_check_passed') is True
                    and isinstance(receipt.get('check'), dict)
                    and receipt['check'].get('integrity_ok') is True):
                pending = True
        if pending and self._guard_enter_serial_selfcheck(state, restored=True):
            phase_prompt=getattr(self.root_public_checker,'selfcheck_phase_prompt',SELF_CHECK_SERIAL_PROMPT)
            if not any(m.get('role') == 'user' and m.get('content') == phase_prompt for m in state.messages):
                state.messages.append({'role':'user','content':phase_prompt})

    def _guard_selfcheck_tool_error(self, state, call):
        if self._guard_serial_selfcheck(state) and call.name in SELF_CHECK_PARALLEL_TOOLS:
            return ('serial_selfcheck_parallel_control_disabled: continue the '
                    'visible-contract checks/local repairs using file or shell '
                    'tools, then call finish_task; no report or spawn is authorized.')
        return ''

    def _guard_schemas(self, state, schemas):
        if (not self.output_guard_enabled or self.depth!=0 or state.tool_repair_mode
                or state.pending_v2_offer is not None or state.pending_parallel_offer is not None
                or {s['function']['name'] for s in schemas}=={'report_frontier_state'}):
            return schemas
        result = schemas + control_schemas()
        if self._guard_run_tests_available(state):
            result.append(run_tests_schema())
        return result

    def _guard_close_rejected(self, state, turn, reason, *, compact=False):
        """Every rejected call gets a matching non-execution receipt, in order."""
        if compact:
            replacement=copy.deepcopy(turn.assistant_message)
            replacement['content']='[Runtime withheld an incomplete or overlong response; no action in this response was executed.]'
            for call in replacement.get('tool_calls') or []:
                call['function']['arguments']='{}'
            state.messages[-1]=replacement
        for call in turn.tool_calls:
            state.messages.append({'role':'tool','name':call.name,'tool_call_id':call.id,
                'content':json.dumps({'ok':False,'completed':False,'not_executed':True,
                    'status':'runtime_output_rejected','reason':reason},ensure_ascii=False)})
        from .handshake_speculation import protocol_complete
        if not protocol_complete(state.messages):
            raise OutputGuardFailure('Rejected tool history could not be safely closed')
        if getattr(self,'_hs_ticket',None) is not None:
            self._hs_discard('output_guard:'+reason)
        self.tracer.emit('output_guard_rejected_protocol_closed',scope_id=self.scope_id,
            step=state.step,reason=reason,rejected_call_ids=[c.id for c in turn.tool_calls],
            history_compacted=compact)

    def _guard_recover(self,state,turn,reason):
        self._guard_close_rejected(state,turn,reason,compact=True)
        self._guard_recoveries+=1
        state.retry_count+=1
        self.tracer.emit('output_guard_recovery',scope_id=self.scope_id,step=state.step,
            reason=reason,attempt=self._guard_recoveries,
            original_narration_chars=len(narration(turn.content).strip()),
            finish_reason=turn.route_info.get('finish_reason'))
        if self._guard_recoveries>=MAX_RECOVERIES:
            state.status='failed'
            raise OutputGuardFailure('Output guard recovery exhausted: '+reason)
        role_completion=(
            'Continue the existing focused check and deliver_files completion contract; '
            'root-only finish_task/report_blocked must not be used by children. '
            if self.depth else
            'Use finish_task only when ready for public check.py, or report_blocked for a real obstacle. ')
        state.messages.append({'role':'user','content':
            'Runtime rejected the previous response ('+reason+'). It is NOT task completion. '
            'Do not continue the prose or regenerate the whole plan in text. Emit the next '
            'bounded tool action now; write code through file tools. '+role_completion+
            'Existing handshake/Offer, metadata, ownership and delivery constraints remain active.'})

    def _guard_receipt(self,state,call,node_id,result):
        tool_node=self.dag.add_node(kind='tool_call',label=call.name,scope_id=self.scope_id,
            status='pending',input={'tool':call.name,'arguments':call.arguments})
        self.dag.add_edge(node_id,tool_node,kind='control')
        self.dag.transition(tool_node,'running')
        status='succeeded' if result.get('ok') else 'failed'
        self.dag.transition(tool_node,status,output=result)
        state.messages.append({'role':'tool','name':call.name,'tool_call_id':call.id,
            'content':json.dumps(result,ensure_ascii=False)})
        self.tracer.emit('tool_result',tool=call.name,tool_call_id=call.id,
            scope_id=self.scope_id,step=state.step,node_id=tool_node,status=status,result=result)
        return tool_node

    def _guard_run_tests(self, state, turn, node_id):
        """Use the same checker instance without requesting task completion."""
        if len(turn.tool_calls) != 1 or turn.tool_calls[0].arguments != {}:
            self._guard_recover(state, turn, 'run_tests_requires_one_empty_argument_call')
            return True, None
        if not self._guard_run_tests_available(state):
            self._guard_recover(state, turn, 'run_tests_requires_root_serial_selfcheck')
            return True, None
        call = turn.tool_calls[0]
        self._check_cancelled()
        context = ToolExecutionContext(node_id=node_id, call_id=call.id,
            scope_id=self.scope_id, cancel_event=self._cancel_event)
        self._progress_recovery_before_batch(state, [call])
        from .providers.base import ProviderCancelled
        from .selfcheck_deadline import SelfcheckDeadlineExceeded
        try:
            with self._guard_selfcheck_deadline_scope(state):
                result = self.root_public_checker.run_tests(self, context)
            self._guard_check_selfcheck_deadline(state)
            self._check_cancelled()
            if not isinstance(result, dict):
                raise TypeError('run_tests checker must return a structured result')
            check = result.get('visible_contract_check')
            if not isinstance(check, dict):
                if result.get('ok') is not False:
                    raise ValueError('run_tests checker did not return visible_contract_check')
                receipt = {**result, 'completed':False, 'public_check_run':False,
                    'hidden_verifier_run':False}
            else:
                passed = (result.get('completion_ready') is True
                          and check.get('status') == 'PASS_BOUNDED'
                          and result.get('integrity_ok', True) is True)
                receipt = {'ok':passed, 'completed':False, 'selfcheck_passed':passed,
                    'public_check_run':False, 'hidden_verifier_run':False,
                    'visible_contract_check':check}
                if not passed:
                    receipt['status'] = check.get('status', 'selfcheck_failed')
                    receipt['error_type'] = 'SelfcheckFailure'
                    receipt['error'] = str(result.get('error') or check.get('error') or receipt['status'])
                    feedback = check.get('selfcheck_feedback') or {}
                    receipt['next_action'] = result.get('next_action') or feedback.get('next_action') or (
                        'Inspect the structured failure, repair the responsible '
                        'test or candidate, preserve existing tests, and rerun run_tests.')
            for field in ('integrity_ok', 'changed_protected_paths', 'completion_blocked'):
                if field in result:
                    receipt[field] = result[field]
        except (SelfcheckDeadlineExceeded, ProviderCancelled):
            raise
        except Exception as exc:
            self._check_cancelled()
            receipt = {'ok':False, 'completed':False, 'status':'tool_error',
                'error_type':type(exc).__name__, 'exception_type':type(exc).__name__,
                'error':str(exc), 'public_check_run':False, 'hidden_verifier_run':False,
                'next_action':'Inspect the tool error and repair the cause before retrying run_tests.'}
        self._guard_receipt(state, call, node_id, receipt)
        observe = getattr(self, '_e1_record_selfcheck', None)
        if (observe is not None and receipt.get('integrity_ok') is not False
                and isinstance(receipt.get('visible_contract_check'), dict)):
            observe(state, receipt['visible_contract_check'], 'run_tests')
        self._recovery_observe_receipts(state, [call], [receipt])
        if receipt.get('completion_blocked'):
            state.status = 'failed'
            raise OutputGuardFailure('Bounded visible-contract completion checks exhausted')
        if self._progress_recovery_after_batch(state, [call], [receipt]):
            from .runtime import RuntimeLimitExceeded
            raise RuntimeLimitExceeded('selfcheck progress recovery exhausted without validated improvement')
        self._guard_recoveries = 0
        return True, None

    def _guard_intercept_turn(self,state,turn,node_id):
        """Return (handled, final text or None); never run this in a worker."""
        if not self.output_guard_enabled:
            return False,None
        if turn.route_info.get('finish_reason')=='length' or turn.route_info.get('output_budget_exhausted'):
            # Retain the existing specialized chunk-write repair when applicable.
            if any(c.name in {'write_file','write_file_chunk'} and '_invalid_json' in c.arguments for c in turn.tool_calls):
                return False,None
            self._guard_recover(state,turn,'incomplete_length')
            return True,None
        if (len(narration(turn.content).strip())>HARD_NARRATIVE_CHARS
                and not (turn.route_info.get('narration_compression_version')=='small-model-narration-v1'
                         and turn.route_info.get('narration_compression_status')=='fallback_original')):
            self._guard_recover(state,turn,'narration_over_1024_chars')
            return True,None
        if self.depth!=0:
            # No new child completion control: retain the original focused
            # check, verified artifact, delivery and short final-answer path.
            self._guard_recoveries=0
            return False,None
        # The legacy handshake/Offer interceptors retain precedence.
        if (getattr(self,'_frontier_report_request_active',False)
                or state.pending_v2_offer is not None or state.pending_parallel_offer is not None):
            return False,None
        if any(call.name == RUN_TESTS_TOOL for call in turn.tool_calls):
            return self._guard_run_tests(state, turn, node_id)
        controls=[c for c in turn.tool_calls if c.name in CONTROL_TOOLS]
        if controls:
            if self._recovery.mode == 'BLOCKED':
                self._recovery_reject_batch(state, turn.tool_calls, node_id)
            if len(turn.tool_calls)!=1:
                self._guard_recover(state,turn,'completion_control_mixed_with_other_calls')
                return True,None
            call=controls[0];field='summary' if call.name=='finish_task' else 'reason'
            value=call.arguments.get(field)
            if set(call.arguments)!={field} or not isinstance(value,str) or not value.strip() or len(value)>1024:
                self._guard_recover(state,turn,'invalid_completion_control_arguments')
                return True,None
            if call.name=='report_blocked':
                self._guard_receipt(state,call,node_id,{'ok':False,'completed':False,'status':'blocked','reason':value})
                self._recovery_change(state, 'block', 'task_explicitly_blocked')
                state.status='failed'
                raise OutputGuardFailure('Task explicitly blocked: '+value)
            if self.root_public_checker is None:
                raise OutputGuardFailure('Root public checker is not configured')
            self._check_cancelled()
            self._guard_check_count+=1
            started=time.time()
            self.tracer.emit('output_guard_public_check_started',scope_id=self.scope_id,
                step=state.step,attempt=self._guard_check_count,command='python3 check.py')
            ctx=ToolExecutionContext(node_id=node_id,call_id=call.id,scope_id=self.scope_id,
                cancel_event=self._cancel_event)
            self._validation_progress_before_batch(state, [call])
            with self._guard_selfcheck_deadline_scope(state):
                result=self.root_public_checker(self,ctx)
            self._guard_check_selfcheck_deadline(state)
            self._check_cancelled()
            passed=result.get('passed') is True and result.get('integrity_ok') is True
            completion_ready=passed and result.get('completion_ready',True) is True
            receipt={'ok':completion_ready,'completed':completion_ready,'public_check_passed':passed,
                'validation_status':'completed' if completion_ready else ('self_check_pending' if passed else 'public_failure'),
                'check':result,'hidden_verifier_run':False}
            checked_node=self._guard_receipt(state,call,node_id,receipt)
            self._recovery_observe_receipts(state, [call], [receipt])
            if self._validation_progress_after_batch(state, [call], [receipt]):
                from .runtime import RuntimeLimitExceeded
                raise RuntimeLimitExceeded('public validation progress recovery exhausted without validated improvement')
            self.tracer.emit('output_guard_public_check_finished',scope_id=self.scope_id,
                step=state.step,attempt=self._guard_check_count,passed=passed,
                integrity_ok=result.get('integrity_ok'),seconds=time.time()-started)
            if passed and not completion_ready:
                entered = self._guard_enter_serial_selfcheck(state)
                observe = getattr(self, '_e1_record_selfcheck', None)
                if observe is not None:
                    observe(state, result.get('visible_contract_check') or {}, 'finish_task')
                self.tracer.emit('visible_contract_completion_deferred',scope_id=self.scope_id,
                    step=state.step,evidence=result.get('visible_contract_check'))
                if result.get('completion_blocked'):
                    state.status='failed'
                    raise OutputGuardFailure('Bounded visible-contract completion checks exhausted')
                if getattr(self,'_hs_ticket',None) is not None:
                    self._hs_discard('visible_contract_completion_required')
                state.messages.append({'role':'user','content':result['completion_instruction']})
                removed = deduplicate_completion_instruction(
                    state.messages, call.id, result['completion_instruction'])
                if removed:
                    self.tracer.emit('visible_contract_instruction_deduplicated',
                        scope_id=self.scope_id, step=state.step,
                        tool_call_id=call.id, removed_characters=removed)
                if entered:
                    state.messages.append({'role':'user','content':getattr(self.root_public_checker,'selfcheck_phase_prompt',SELF_CHECK_SERIAL_PROMPT)})
                self._guard_recoveries=0
                return True,None
            if passed:
                final,_=self._handle_final_answer(state,value,checked_node)
                return True,final
            if self._guard_check_count>=MAX_ROOT_CHECKS:
                state.status='failed'
                raise OutputGuardFailure('Public root check failed after three completion requests')
            state.messages.append({'role':'user','content':
                'Public check.py failed; completion was rejected. Use its actual error in '
                'the tool result to repair the implementation and focused tests. Do not '
                'claim hidden-verifier success. Then request finish_task again.'})
            self._guard_recoveries=0
            return True,None
        if not turn.tool_calls:
            self._guard_recover(state,turn,'unstructured_root_completion')
            return True,None
        self._guard_recoveries=0
        return False,None
