# Shared prebuilt base for the xi474 benchmark matrix.
#
# This intentionally sits on top of the existing DSH fixture image so Nanobot
# and DSH stay preinstalled, while Codex, OpenCode and LangGraph are baked in
# once instead of being installed inside every trial container.
FROM harness-v3-fixture-logvault-dsh:2026-10-23

ARG CODEX_VERSION=latest
ARG OPENCODE_VERSION=latest
ARG NPM_REGISTRY=https://registry.npmmirror.com

# Codex and OpenCode are CLI harnesses, not task dependencies; pin at build
# time and keep them in the shared layer.
RUN npm install -g --registry="${NPM_REGISTRY}" \
        "@openai/codex@${CODEX_VERSION}" \
        "opencode-ai@${OPENCODE_VERSION}" \
    && codex --version \
    && opencode --version

# Harbor's LangGraph agent checks for this exact venv path and skips its own
# install step when the interpreter exists.
RUN python3 -m venv /installed-agent/langgraph-venv \
    && /installed-agent/langgraph-venv/bin/pip install --disable-pip-version-check --no-cache-dir \
        "langgraph==1.2.16" \
        "langgraph-sdk==0.4.9" \
        "websockets==17.3" \
        "openai>=1.68.0,<3.0.0" \
    && /installed-agent/langgraph-venv/bin/python -c "import langgraph; print('langgraph-ready')"

ENV PATH="/installed-agent/langgraph-venv/bin:${PATH}"
