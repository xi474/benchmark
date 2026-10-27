# Service boundary hardening

Keep all public function signatures.

* `sessions/tokens.py`: URL-safe HMAC tokens, expiry and subject validation, constant-time signature comparison; malformed data returns `None`.
* `webhooks/verify.py`: validate timestamp skew, HMAC the exact `timestamp.body` bytes, prevent replay through the supplied mutable nonce set; return a reason string.
* `exports/paths.py`: resolve a tenant-relative export below its tenant root, reject absolute/traversal/symlink escapes, and create only the tenant directory.

Detailed constants are in the adjacent `policy.json` files. Do not modify policy files or `check.py`.


The hardening must preserve internal helper APIs as well as facades. Sessions owns `codec.py`, `claims.py`, and `tokens.py`; webhooks owns `signature.py`, `replay.py`, and `verify.py`; exports owns `tenant.py`, `safe_path.py`, and `paths.py`. Focused package checks are provided and are part of the public contract.
