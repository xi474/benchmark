"""Bounded next-action recovery after three verified no-progress attempts.

Recovery uses the next ordinary model turn, never a separate planning call.
Reports/Offers are not business progress; complete original history is retained.
"""
import hashlib
import json

VERSION = 'verified-progress-recovery-v1'
CONTROL = frozenset({'report_frontier_state', 'choose_execution_mode',
                     'choose_execution_mode_v2', 'spawn_subtasks'})
NO_EVIDENCE = frozenset({'not_executed', 'duplicate_in_same_turn',
                         'duplicate_no_new_evidence', 'duplicate_tool_circuit_breaker',
                         'duplicate_write_suppressed', '_semserve_reused'})


class ProgressRecoveryMixin:
    def _progress_recovery_init(self):
        self._progress_recovery_active = False
        self._progress_recovery_streak = 0
        self._progress_recovery_attempts = 0
        self._progress_recovery_seen = set()
        self._progress_recovery_blocked = {}
        self._progress_recovery_fingerprint = None
        self._progress_recovery_batch = None

    def _progress_recovery_snapshot(self):
        if not hasattr(self, '_cross_workspace'):
            return None, False
        _, certain = self._cross_workspace.snapshot()
        return self._cross_workspace.fingerprint, certain

    def _progress_recovery_before_batch(self, state, calls):
        if not self.output_guard_enabled or all(c.name in CONTROL for c in calls):
            self._progress_recovery_batch = None
            return
        if self._progress_recovery_fingerprint is None:
            self._progress_recovery_fingerprint, _ = self._progress_recovery_snapshot()
        self._progress_recovery_batch = {
            'was_active': self._progress_recovery_active,
            'fingerprint': self._progress_recovery_fingerprint,
        }

    @staticmethod
    def _progress_recovery_fact(call, result):
        if call.name in CONTROL or any(result.get(k) for k in NO_EVIDENCE):
            return None
        # Observe actual receipts, including a genuinely new failed check.
        # Runtime clocks/counters are not new business evidence.
        clean = {k:v for k,v in result.items() if k not in {
            'runtime_fact', 'seconds', 'elapsed_seconds', 'progress_version',
            'workspace_epoch', '_semserve_operation_key',
        }}
        return (call.name, hashlib.sha256(json.dumps(
            clean, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest())

    def _progress_recovery_clear(self, state, reason):
        self._recovery_change(state, 'resolve', 'tool_progress')
        if self._progress_recovery_active:
            self.tracer.emit('progress_recovery_resolved', scope_id=self.scope_id,
                             step=state.step, reason=reason,
                             recovery_attempts=self._progress_recovery_attempts)
        self._progress_recovery_active = False
        self._progress_recovery_streak = 0
        self._progress_recovery_attempts = 0
        self._progress_recovery_blocked = {}

    def _progress_recovery_feedback(self, state, reason):
        prompt = {
            'reason': reason,
            'consecutive_no_progress_batches': self._progress_recovery_streak,
            'recovery_attempt': self._progress_recovery_attempts + 1,
            'maximum_recovery_business_turns': 2,
            'stalled_actions': list(self._progress_recovery_blocked.values())[-8:],
            'required_action': (
                'Advance the original unfinished task now. Do not repeat the listed '
                'operations. Already persisted identical content needs no further write. '
                'Choose a genuine content repair, implement an unfinished part, obtain '
                'new evidence, or run a required check not already observed. If blocked, '
                'use report_blocked with the concrete reason. Task completion must still '
                'satisfy all existing checks and delivery contracts.'),
            'authority': 'Runtime receipts and live file hashes only; no precomputed task plan',
        }
        state.messages.append({'role':'user', 'content':
                               '[RUNTIME_PROGRESS_RECOVERY]\n' + json.dumps(prompt, ensure_ascii=False)})
        self.tracer.emit('progress_recovery_requested', scope_id=self.scope_id,
                         step=state.step, reason=reason,
                         recovery_attempt=self._progress_recovery_attempts + 1,
                         stalled_action_count=len(self._progress_recovery_blocked))

    def _progress_recovery_operation_key(self, call):
        return self._tool_operation_key(call)

    def _progress_recovery_preflight(self, state, call):
        if not self._progress_recovery_active or call.name in CONTROL:
            return None
        key = self._progress_recovery_operation_key(call)
        if key not in self._progress_recovery_blocked:
            return None
        # A real external edit may make a formerly redundant read/write useful.
        fingerprint, certain = self._progress_recovery_snapshot()
        if certain and fingerprint != self._progress_recovery_fingerprint:
            self._progress_recovery_clear(state, 'external_workspace_change')
            self._progress_recovery_fingerprint = fingerprint
            return None
        result = {
            'ok': False, 'status':'progress_recovery_action_rejected',
            'not_executed': True, 'completed': False, 'rerun_required':False,
            'choose_new_action':True,
            'error':'Recovery requires a different action. This exact operation was already verified to make no progress.',
            'operation_sha256':hashlib.sha256(key.encode()).hexdigest(),
        }
        self.tracer.emit('progress_recovery_action_rejected', scope_id=self.scope_id,
                         step=state.step, call_id=call.id, tool=call.name,
                         operation_sha256=result['operation_sha256'], executed=False)
        return result

    def _progress_recovery_after_batch(self, state, calls, results):
        batch = self._progress_recovery_batch
        self._progress_recovery_batch = None
        if batch is None:
            return False
        fingerprint, certain = self._progress_recovery_snapshot()
        changed = certain and fingerprint != batch['fingerprint']
        novel = False
        target_stall = False
        for call, result in zip(calls, results):
            if call.name in CONTROL:
                continue
            fact = self._progress_recovery_fact(call, result)
            if fact is not None:
                novel |= fact not in self._progress_recovery_seen
                self._progress_recovery_seen.add(fact)
            if any(result.get(k) for k in NO_EVIDENCE):
                key = self._progress_recovery_operation_key(call)
                self._progress_recovery_blocked[key] = {
                    'tool':call.name, 'path':result.get('path', call.arguments.get('path')),
                    'operation_sha256':hashlib.sha256(key.encode()).hexdigest(),
                    'content_already_present':bool(result.get('content_present')),
                    'current_file_sha256':result.get('current_file_sha256'),
                }
            # Per-target no-op counts survive unrelated workspace mutations.
            target_stall |= (result.get('duplicate_write_suppressed') is True
                             and result.get('repeat_count',0) >= 4)
        self._progress_recovery_fingerprint = fingerprint
        if changed or novel:
            self._progress_recovery_clear(state, 'verified_workspace_or_evidence_change')
            return False
        if not certain:
            return False  # An uncertain snapshot cannot justify coercive action.
        self._progress_recovery_streak += 1
        if batch['was_active'] and self._progress_recovery_active:
            remaining = self._recovery_change(state, 'consume', 'tool_progress', self._recovery_batch(state))
            self._progress_recovery_attempts = 2 - remaining
            if self._progress_recovery_attempts >= 2:
                self.tracer.emit('progress_recovery_exhausted', scope_id=self.scope_id,
                                 step=state.step, recovery_attempts=2)
                return True
            self._progress_recovery_feedback(state, 'recovery_action_made_no_verified_progress')
        elif self._progress_recovery_streak >= 3 or target_stall:
            self._progress_recovery_active = True
            self._progress_recovery_attempts = 0
            self._recovery_change(state, 'begin', 'tool_progress', 'verified_no_progress', 2,
                                  discard_reason='progress_recovery_required')
            if getattr(self, '_hs_ticket', None) is not None:
                self._hs_discard('progress_recovery_required')
            self._progress_recovery_feedback(state,
                'three_same_target_noop_writes' if target_stall else 'three_no_progress_business_batches')
        return False
