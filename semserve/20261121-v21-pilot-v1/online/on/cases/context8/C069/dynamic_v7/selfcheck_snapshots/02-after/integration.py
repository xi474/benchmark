import base64
import json


def _b64url(obj):
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def _encode_ssh(roles, resources, traits, login_time, expires):
    obj = {
        "roles": roles,
        "allowed_resources": resources,
        "extensions": traits,
        "login_time": login_time,
        "expires": expires,
    }
    return "SSH-MODEL1." + _b64url(obj)


def _encode_tls(user_name, active_requests, login_time, expires):
    obj = {
        "user": user_name,
        "active_requests": active_requests,
        "login_time": login_time,
        "expires": expires,
    }
    return "TLS-MODEL1." + _b64url(obj)


def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    user = payload.get("user", {})
    start_time = payload.get("start_time", 0)
    session_ttl = payload.get("session_ttl")
    events = payload.get("events", [])
    initial_id = payload.get("initial_id", "s0")

    # left: user_history -> {position_string: user_snapshot}
    # right: grant_catalog -> {request_id: {approved, expiry, roles, resources}}
    catalog = right if isinstance(right, dict) else {}

    # Backend user state, mutated by update_user events.
    backend_user = {
        "name": user.get("name"),
        "roles": list(user.get("roles", [])),
        "traits": dict(user.get("traits", {})),
    }

    # Initial session s0.
    sessions = {}
    sessions[initial_id] = {
        "id": initial_id,
        "login_time": start_time,
        "expiry": start_time + session_ttl,
        "cached_user": {
            "name": backend_user["name"],
            "roles": list(backend_user["roles"]),
            "traits": dict(backend_user["traits"]),
        },
        "active_requests": [],  # list of request ids in assume order
    }

    session_ids = [initial_id]
    replies = []

    for ev in events:
        op = ev.get("op")
        if op == "update_user":
            if "roles" in ev:
                backend_user["roles"] = list(ev["roles"])
            if "traits" in ev:
                backend_user["traits"] = dict(ev["traits"])
            continue

        if op != "renew":
            continue

        rid = ev.get("id")
        prev_id = ev.get("prev")
        now = ev.get("time")
        reload_user = ev.get("reload_user", False)
        switchback = ev.get("switchback", False)
        access_request = ev.get("access_request")

        prev = sessions.get(prev_id)
        if prev is None:
            replies.append({"id": rid, "status": "expired"})
            continue

        if prev["expiry"] <= now:
            replies.append({"id": rid, "status": "expired"})
            continue

        # Determine cached user for the new session.
        if reload_user:
            cached_user = {
                "name": backend_user["name"],
                "roles": list(backend_user["roles"]),
                "traits": dict(backend_user["traits"]),
            }
        else:
            cached_user = {
                "name": prev["cached_user"]["name"],
                "roles": list(prev["cached_user"]["roles"]),
                "traits": dict(prev["cached_user"]["traits"]),
            }

        # Determine active requests for the new session.
        if switchback:
            active_requests = []
        else:
            active_requests = list(prev["active_requests"])

        if access_request is not None:
            req = catalog.get(access_request)
            if req is None or not req.get("approved") or req.get("expiry") is None or req["expiry"] <= now:
                replies.append({"id": rid, "status": "request_unavailable"})
                continue
            has_resources = bool(req.get("resources"))
            if has_resources:
                # A resource request cannot be assumed if any resource request is already active.
                conflict = False
                for existing_id in active_requests:
                    existing = catalog.get(existing_id)
                    if existing and existing.get("resources"):
                        conflict = True
                        break
                if conflict:
                    replies.append({"id": rid, "status": "resource_already_active"})
                    continue
                active_requests.append(access_request)
            else:
                active_requests.append(access_request)

        # Deduplicate role requests while preserving order.
        seen = set()
        deduped = []
        for req_id in active_requests:
            if req_id not in seen:
                seen.add(req_id)
                deduped.append(req_id)
        active_requests = deduped

        # Compute roles and resources.
        roles = set(cached_user["roles"])
        resources = set()
        for req_id in active_requests:
            req = catalog.get(req_id)
            if req is None:
                continue
            roles.update(req.get("roles", []))
            resources.update(req.get("resources", []))

        roles = sorted(roles)
        resources = sorted(resources)

        # Compute expiry.
        expiry = now + session_ttl
        for req_id in active_requests:
            req = catalog.get(req_id)
            if req is not None and req.get("expiry") is not None:
                expiry = min(expiry, req["expiry"])

        new_session = {
            "id": rid,
            "login_time": prev["login_time"],
            "expiry": expiry,
            "cached_user": cached_user,
            "active_requests": active_requests,
        }
        sessions[rid] = new_session
        session_ids.append(rid)

        ssh = _encode_ssh(roles, resources, cached_user["traits"], new_session["login_time"], expiry)
        tls = _encode_tls(cached_user["name"], sorted(active_requests), new_session["login_time"], expiry)
        replies.append({
            "id": rid,
            "status": "ok",
            "ssh_certificate": ssh,
            "tls_certificate": tls,
        })

    return {
        "replies": replies,
        "session_ids": session_ids,
    }
