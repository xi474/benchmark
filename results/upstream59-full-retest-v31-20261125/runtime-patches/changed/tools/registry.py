from __future__ import annotations

import threading
import traceback
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from agent_runtime_demo.validation import Draft202012Validator

from agent_runtime_demo.tools.base import (
    Tool,
    ToolCancelled,
    ToolConcurrency,
    ToolExecutionContext,
)


_DEFAULT_SERIALIZATION_KEY = "tool-registry:serial"


class ToolRegistry:
    def __init__(
        self,
        tools: Iterable[Tool],
        closers: Iterable[Callable[[], None]] = (),
    ):
        self._tools: dict[str, Tool] = {}
        self._argument_validators: dict[str, Any] = {}
        self._closers = list(closers)
        self._condition = threading.Condition(threading.RLock())
        self._execution_locks: dict[str, threading.RLock] = {}
        self._active_calls = 0
        self._closing = False
        self._closed = False
        self._closing_thread_id: int | None = None
        for tool in tools:
            self.add(tool)

    def add(self, tool: Tool) -> None:
        with self._condition:
            if self._closing or self._closed:
                raise RuntimeError("Tool registry is closed")
            if tool.name in self._tools:
                raise ValueError(f"Duplicate tool name: {tool.name}")
            schema = tool.schema().get("function", {}).get("parameters")
            if schema is not None:
                if Draft202012Validator is None:
                    raise RuntimeError("jsonschema is required for tool argument validation")
                Draft202012Validator.check_schema(schema)
                self._argument_validators[tool.name] = Draft202012Validator(schema)
            self._tools[tool.name] = tool

    def add_many(self, tools: Iterable[Tool]) -> None:
        for tool in tools:
            self.add(tool)

    @property
    def names(self) -> frozenset[str]:
        with self._condition:
            return frozenset(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        with self._condition:
            tools = list(self._tools.values())
        return [tool.schema() for tool in tools]

    def metadata(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> ToolConcurrency:
        """Return executable concurrency policy, defaulting unknown tools to serial.

        The optional ``arguments`` supports tools whose serialization key is a
        callable.  This lets a future tool serialize by resource without making
        the registry trust model-supplied safety declarations.
        """

        with self._condition:
            tool = self._tools.get(name)
        if tool is None:
            return ToolConcurrency(concurrency_key=_DEFAULT_SERIALIZATION_KEY)
        return self._metadata_for_tool(tool, arguments or {})

    def execution_policy(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> ToolConcurrency:
        """Scheduler-facing alias for :meth:`metadata`."""

        return self.metadata(name, arguments)

    def can_run_in_parallel(self, name: str) -> bool:
        """Convenience query for schedulers deciding whether to fan out calls."""

        return self.metadata(name).parallel_safe

    def can_speculate_readonly(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        trusted_names: frozenset[str] = frozenset(),
    ) -> bool:
        """Return whether a tool is locally trusted for side-effect-free pre-execution.

        Native tools opt in with ``speculation_safe=True``.  Remote MCP
        annotations never reach this path automatically; an operator must add
        the fully qualified tool name to ``trusted_names`` after auditing it.
        """

        with self._condition:
            tool = self._tools.get(name)
        if tool is None:
            return False
        policy = self._metadata_for_tool(tool, arguments or {})
        native_opt_in = getattr(tool, "speculation_safe", False) is True
        operator_opt_in = name in trusted_names
        return bool((native_opt_in and policy.read_only) or operator_opt_in)

    def can_reuse_result(self, name: str, arguments: dict[str, Any]) -> bool:
        """Allow memoization only for explicitly trusted, stable read-only tools.

        ``result_cache_safe=True`` promises that equal arguments produce the
        same result throughout an attempt, including across child execution
        and external changes. Read-only alone does not imply this: file reads,
        directory searches and tests depend on mutable workspace state. Remote
        annotations and model-supplied arguments cannot opt a tool into reuse.
        Side-effecting calls must execute even when their arguments repeat.
        """
        with self._condition:
            tool = self._tools.get(name)
        return bool(
            tool is not None
            and getattr(tool, "result_cache_safe", False) is True
            and self._metadata_for_tool(tool, arguments).read_only
        )

    def speculation_snapshot(self, name: str, arguments: dict[str, Any]) -> str | None:
        """Return a best-effort state token used to invalidate stale results."""

        with self._condition:
            tool = self._tools.get(name)
        if tool is None:
            return None
        snapshot = getattr(tool, "speculation_snapshot", None)
        if not callable(snapshot):
            return None
        try:
            value = snapshot(arguments)
        except Exception:
            return None
        return str(value) if value is not None else None

    def extract_verified_artifact(
        self,
        name: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Return a tool-attested artifact without trusting model-declared metadata.

        A tool may opt in with ``extract_verified_artifact(arguments, result)``.
        The extractor runs only after the tool has executed, and the registry
        accepts only a mapping with non-empty string ``content``.  Extractor
        failures reduce to no artifact rather than changing tool success.
        """

        with self._condition:
            tool = self._tools.get(name)
        if tool is None or result.get("ok") is not True:
            return None
        extractor = getattr(tool, "extract_verified_artifact", None)
        if not callable(extractor):
            return None
        try:
            raw = extractor(dict(arguments), dict(result))
        except Exception:
            return None
        if not isinstance(raw, Mapping):
            return None
        artifact = dict(raw)
        content = artifact.get("content")
        if not isinstance(content, str) or not content.strip():
            return None
        artifact["content"] = content.strip()
        return artifact

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        context: ToolExecutionContext | None = None,
    ) -> dict[str, Any]:
        with self._condition:
            tool = self._tools.get(name)
            if tool is None:
                return {"ok": False, "error": f"Unknown tool: {name}",
                        "error_type": "UnknownToolError", "status": "tool_error",
                        "not_executed": True, "next_action": "Use a tool exposed in the current request."}
            if self._closing or self._closed:
                return {"ok": False, "error": "Tool registry is closed"}
            validator = self._argument_validators.get(name)
            errors = list(validator.iter_errors(arguments)) if validator is not None else []
            if errors:
                details = []
                for error in errors[:5]:
                    field = ".".join(map(str, error.absolute_path)) or "$"
                    if error.validator == "maxLength" and isinstance(error.instance, str):
                        actual_length = len(error.instance)
                        limit = error.validator_value
                        details.append({"field": field, "validator": "maxLength",
                                        "limit": limit, "actual_length": actual_length,
                                        "message": f"String length {actual_length} exceeds maximum {limit} characters."})
                    else:
                        details.append({"field": field, "message": error.message[:1200]})
                detail = "; ".join(f"{e['field']}: {e['message']}" for e in details)
                next_action = "Correct the listed fields using this tool's current parameter schema, then retry. No tool action was executed."
                chunk_validator = self._argument_validators.get("write_file_chunk")
                if name == "write_file" and chunk_validator is not None and any(
                    e.get("validator") == "maxLength" and e["field"] == "content" for e in details
                ):
                    chunk_limit = chunk_validator.schema.get("properties", {}).get("content", {}).get("maxLength")
                    if isinstance(chunk_limit, int) and chunk_limit > 0:
                        next_action = (
                            f"Use ordered write_file_chunk calls with the same path and at most {chunk_limit} characters of content per chunk. "
                            "For the first chunk use expected_offset=0 and truncate=true only when replacing the target is intended; "
                            "otherwise use truncate=false. For later chunks use truncate=false and the returned next_offset as expected_offset. "
                            "Correct any other listed fields. No tool action was executed."
                        )
                return {"ok": False, "status": "invalid_arguments", "not_executed": True,
                        "error_type": "ToolInvalidArgumentsError", "exception_type": "ToolInvalidArgumentsError",
                        "error": f"Invalid arguments for {name}: {detail}", "validation_errors": details,
                        "next_action": next_action}
            policy = self._metadata_for_tool(tool, arguments)
            execution_lock = self._lock_for(policy)
            self._active_calls += 1
        try:
            if execution_lock is None:
                result = self._execute_tool(tool, arguments, context)
            else:
                with execution_lock:
                    result = self._execute_tool(tool, arguments, context)
            observer = getattr(self, '_guard_workspace_epoch', None)
            if name == 'shell' and observer is not None and result.get('output_path'):
                path = observer.root / result['output_path']
                if path.resolve().is_relative_to(observer.root / '.semserve/visible_checks/tool-output'):
                    with observer.lock:
                        observer.excluded_paths.add(path.resolve())
            return result
        finally:
            with self._condition:
                self._active_calls -= 1
                if self._active_calls == 0:
                    self._condition.notify_all()

    @staticmethod
    def _execute_tool(
        tool: Tool,
        arguments: dict[str, Any],
        context: ToolExecutionContext | None,
    ) -> dict[str, Any]:
        try:
            if context is not None:
                context.raise_if_cancelled()
                execute_with_context = getattr(tool, "execute_with_context", None)
                if callable(execute_with_context):
                    return ToolRegistry._error_feedback(tool.name, execute_with_context(arguments, context))
            return ToolRegistry._error_feedback(tool.name, tool.execute(arguments))
        except ToolCancelled as exc:
            return {
                "ok": False,
                "status": "cancelled",
                "error": str(exc),
                "exception_type": type(exc).__name__,
                "error_type": type(exc).__name__,
            }
        except Exception as exc:
            return {
                "ok": False,
                "status": "tool_error",
                "error": str(exc),
                "exception_type": type(exc).__name__,
                "error_type": type(exc).__name__,
                "traceback": traceback.format_exc()[-5000:],
                "next_action": "Inspect the error and relevant file or input; correct the cause before retrying this action.",
            }

    @staticmethod
    def _error_feedback(name: str, result: dict[str, Any]) -> dict[str, Any]:
        """Add actionable errors without changing existing admission or success semantics."""
        if result.get("ok") is not False:
            return result
        feedback = dict(result)
        feedback.setdefault("error_type", feedback.get("exception_type") or feedback.get("status") or "ToolExecutionError")
        feedback.setdefault("error", str(feedback.get("output") or f"{name} failed")[-1800:])
        if feedback.get("status") != "cancelled":
            feedback.setdefault("next_action", "Inspect the tool error, correct the relevant input or source, then rerun the failed action. A failed call is not completion evidence.")
        return feedback

    def close(self) -> None:
        current_thread_id = threading.get_ident()
        with self._condition:
            if self._closed:
                return
            if self._closing:
                # A closer may defensively call close() again.  Returning for
                # that same thread avoids self-deadlock; other callers wait for
                # the one owner to finish.
                if self._closing_thread_id == current_thread_id:
                    return
                while not self._closed:
                    self._condition.wait()
                return
            self._closing = True
            self._closing_thread_id = current_thread_id
            while self._active_calls:
                self._condition.wait()
            closers = list(reversed(self._closers))
            self._closers.clear()

        first_error: BaseException | None = None
        try:
            for closer in closers:
                try:
                    closer()
                except BaseException as exc:
                    if first_error is None:
                        first_error = exc
        finally:
            with self._condition:
                self._closed = True
                self._closing = False
                self._closing_thread_id = None
                self._condition.notify_all()
        if first_error is not None:
            raise first_error

    def _lock_for(self, policy: ToolConcurrency) -> threading.RLock | None:
        if policy.parallel_safe:
            return None
        key = policy.concurrency_key or _DEFAULT_SERIALIZATION_KEY
        lock = self._execution_locks.get(key)
        if lock is None:
            lock = threading.RLock()
            self._execution_locks[key] = lock
        return lock

    @staticmethod
    def _metadata_for_tool(
        tool: Tool,
        arguments: dict[str, Any],
    ) -> ToolConcurrency:
        parallel_safe = getattr(tool, "parallel_safe", False) is True
        read_only = getattr(tool, "read_only", False) is True

        raw_key = getattr(tool, "concurrency_key", None)
        if callable(raw_key):
            try:
                raw_key = raw_key(arguments)
            except Exception:
                # A broken dynamic policy must reduce, never increase, safety.
                raw_key = None
        serialization_key = raw_key if isinstance(raw_key, str) and raw_key else None
        if not parallel_safe and serialization_key is None:
            serialization_key = _DEFAULT_SERIALIZATION_KEY

        raw_hints = getattr(tool, "safety_hints", {})
        safety_hints = dict(raw_hints) if isinstance(raw_hints, Mapping) else {}
        return ToolConcurrency(
            parallel_safe=parallel_safe,
            read_only=read_only,
            concurrency_key=serialization_key,
            safety_hints=safety_hints,
        )
