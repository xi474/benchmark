# Tenant platform v2 upgrade

The public entry points below must keep their signatures. Existing implementations contain incomplete legacy behavior.

* `identity/service.py::authorize(request, policy)` must normalize roles, enforce tenant equality, honor deny lists, and return a JSON-safe decision with a stable reason.
* `billing/service.py::invoice(events, pricing)` must ignore duplicate event ids, apply per-tenant decimal rates and credits, round half-up to cents, and return stable line ordering.
* `notify/service.py::build_delivery(message, preferences)` must choose an enabled channel, escape untrusted HTML, and derive a deterministic idempotency key.

Module-specific examples live in each package's `contract.json`. Do not modify contract files or `check.py`. Preserve the three public entry points and run `python check.py` before completion.


The upgrade is intentionally spread across the implementation units below; public tests import the helpers directly as well as the service facade.
Identity owns `normalize.py`, `policy.py`, and `service.py`. Billing owns `money.py`, `events.py`, and `service.py`. Notification owns `channels.py`, `render.py`, and `service.py`. Each package contains `check_module.py`; all three module checks and the root integration check must pass.
