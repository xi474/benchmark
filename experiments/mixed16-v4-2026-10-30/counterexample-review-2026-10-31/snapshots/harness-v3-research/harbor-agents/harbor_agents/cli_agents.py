"""Harbor agent wrappers for the CLI harnesses.

The wrappers only add the C1 delegation-policy upload step; the built-in
Harbor agents own installation, native log capture and ATIF conversion.
C0 runs leave ``HARNESS_DELEGATION_POLICY_FILE`` unset, so the wrapper is a
no-op.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, override

from harbor.agents.installed.base import NonZeroAgentExitCodeError
from harbor.agents.installed.claude_code import ClaudeCode as _HarborClaudeCode
from harbor.agents.installed.codex import Codex as _HarborCodex
from harbor.agents.installed.opencode import OpenCode as _HarborOpenCode
from harbor.environments.base import BaseEnvironment

from .common import upload_delegation_policy

CODEX_MULTI_AGENT_CONFIG: dict[str, Any] = {
    # Codex 0.164 defaults to the WebSocket Responses transport and attempts a
    # remote-compaction request over wss://. DeepSeek exposes the HTTP
    # Responses endpoint but not that WebSocket endpoint (405), so pin an
    # HTTP-only provider.
    "model_provider": "deepseek_http",
    "model_providers": {
        "deepseek_http": {
            "name": "DeepSeek HTTP",
            "base_url": "https://api.deepseek.com",
            "wire_api": "responses",
            "requires_openai_auth": True,
            "supports_websockets": False,
        }
    },
    "features": {
        "multi_agent_v2": {
            "enabled": True,
            # Soft, complexity-gated policy: delegate only when the task has
            # meaningful independent branches, not for small/linear tasks.
            "multi_agent_mode_hint_text": (
                "Multi-agent delegation is available. Consider spawning a subagent "
                "when the task has meaningful independent branches (for example "
                "separate modules, sources, or verification tracks) and delegation "
                "could save time or improve quality. Do not spawn subagents for "
                "small or strictly linear tasks. When you delegate, give each "
                "subagent a disjoint write scope and a concrete deliverable, "
                "continue useful work yourself, and wait for required subagent "
                "results before finalizing."
            ),
        }
    }
}


class ClaudeCodeAgent(_HarborClaudeCode):
    """Claude Code + optional C1 policy in ``/app/CLAUDE.md``."""

    def _resolved_model_name(self) -> str | None:
        # Harbor's base implementation keeps the ``provider/`` prefix whenever
        # a custom base URL is configured.  Claude Code forwards the value
        # verbatim to the Anthropic endpoint, which only accepts bare model
        # names such as ``deepseek-flash``.
        if self.model_name:
            return self.model_name.split("/", 1)[-1]
        return None

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        await super().install(environment)
        await upload_delegation_policy(
            self, environment, default_target="/app/CLAUDE.md"
        )


CODEX_CATALOG_PATH = "/tmp/codex-model-catalog.json"
CODEX_CATALOG_FILE = (
    Path(__file__).resolve().parent.parent / "config" / "codex-model-catalog.json"
)


class CodexAgent(_HarborCodex):
    """Codex CLI + complexity-gated multi-agent config + optional C1 policy."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Harbor loads the native config in Codex.__init__, so inject the
        # default before calling super(). An explicit caller config wins.
        config = dict(kwargs.get("config") or CODEX_MULTI_AGENT_CONFIG)
        # Codex's built-in catalog does not know DeepSeek. A local catalog is
        # required for freeform apply_patch/context metadata; without it Codex
        # falls back to generic metadata and drops its patch tool.
        config["model_catalog_json"] = CODEX_CATALOG_PATH
        kwargs["config"] = config
        super().__init__(*args, **kwargs)

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        if CODEX_CATALOG_FILE.exists():
            encoded = base64.b64encode(CODEX_CATALOG_FILE.read_bytes()).decode("ascii")
            await self.exec_as_agent(
                environment,
                command=(
                    "set -eu; "
                    f"printf %s {encoded} | base64 -d > {CODEX_CATALOG_PATH}; "
                    f"test -s {CODEX_CATALOG_PATH}"
                ),
            )
        probe = await environment.exec(
            command="command -v codex && codex --version", cwd="/app"
        )
        if probe.return_code != 0:
            await super().install(environment)
        await upload_delegation_policy(
            self, environment, default_target="/app/AGENTS.md"
        )


class OpenCodeAgent(_HarborOpenCode):
    """OpenCode + optional C1 policy in ``/app/AGENTS.md``."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raw = os.environ.get("HARNESS_OPENCODE_CONFIG")
        if raw and "opencode_config" not in kwargs:
            config = json.loads(raw)
            api_key = os.environ.get("HARNESS_API_KEY")
            if api_key:
                for provider in (config.get("provider") or {}).values():
                    if isinstance(provider, dict):
                        provider.setdefault("options", {})["apiKey"] = api_key
            kwargs["opencode_config"] = config
        super().__init__(*args, **kwargs)

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        probe = await environment.exec(
            command="command -v opencode && opencode --version", cwd="/app"
        )
        if probe.return_code != 0:
            node_probe = await environment.exec(
                command="command -v node", cwd="/app"
            )
            if node_probe.return_code != 0:
                # Prepared task images are python-only; let Harbor bootstrap
                # Node/OpenCode instead of assuming the shared base image.
                await super().install(environment)
            else:
                # The shared base image already has Node/npm.
                await self.exec_as_agent(
                    environment,
                    command=(
                        "set -euo pipefail; "
                        "node --version; npm --version; "
                        "npm i -g --registry=https://registry.npmmirror.com opencode-ai@latest; "
                        "opencode --version"
                    ),
                )
        await upload_delegation_policy(
            self, environment, default_target="/app/AGENTS.md"
        )

    @override
    async def run(
        self, instruction: str, environment: BaseEnvironment, context: Any
    ) -> None:
        try:
            await super().run(instruction, environment, context)
        except NonZeroAgentExitCodeError:
            # OpenCode can finish the final answer and then die with EPIPE while
            # flushing its JSON stream. Treat a logged stop as a completed run;
            # any other non-zero exit remains a real failure.
            result = await environment.exec(
                command=(
                    "grep -q '\"type\":\"step_finish\"' /logs/agent/opencode.txt "
                    "&& grep -q '\"reason\":\"stop\"' /logs/agent/opencode.txt"
                ),
                cwd="/app",
            )
            if result.return_code != 0:
                raise
