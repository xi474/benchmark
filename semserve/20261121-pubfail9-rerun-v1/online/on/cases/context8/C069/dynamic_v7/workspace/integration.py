import base64
import copy
import json


def _b64url(obj):
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def _encode_ssh(roles, resources, extensions, login_time, expires):
    obj = {
        "roles": roles,
        "allowed_resources": resources,
        "extensions": extensions,
        "login_time": login_time,
        "expires": expires,
    }
    return "SSH-MODEL1." + _b64url(obj)


def _encode_tls(user, active_requests, login_time, expires):
    obj = {
        "user": user,
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
    access_requests = payload.get("access_requests", {})
    events = payload.get("events", [])
    initial_id = payload.get("initial_id", "s0")

    # left: user_history snapshots keyed by event position string
    # right: grant_catalog entries keyed by request id
    history = left if isinstance(left, dict) else {}
    catalog = right if isinstance(right, dict) else {}

    # Backend user state, mutated by update_user events.
    backend_user = copy.deepcopy(user)

    # s0 session
    sessions = {}
    sessions[initial_id] = {
        "user": copy.deepcopy(user),
        "login_time": start_time,
        "expiry": start_time + session_ttl,
        "active_requests": [],  # list of request ids in assume order
    }

    session_ids = [initial_id]
    replies = []

    for idx, event in enumerate(events):
        op = event.get("op")
        if op == "update_user":
            if "roles" in event:
                backend_user["roles"] = list(event["roles"])
            if "traits" in event:
                backend_user["traits"] = copy.deepcopy(event["traits"])
            continue

        if op != "renew":
            continue

        rid = event.get("id")
        prev_id = event.get("prev")
        now = event.get("time")
        reload_user = event.get("reload_user", False)
        switchback = event.get("switchback", False)
        access_request = event.get("access_request")

        prev = sessions.get(prev_id)
        if prev is None:
            replies.append({"id": rid, "status": "expired"})
            continue

        if prev["expiry"] <= now:
            replies.append({"id": rid, "status": "expired"})
            continue

        # Determine cached user for the new session.
        if reload_user:
            cached_user = copy.deepcopy(backend_user)
        else:
            cached_user = copy.deepcopy(prev["user"])

        # Determine active requests.
        if switchback:
            active_requests = []
        else:
            active_requests = list(prev["active_requests"])

        if access_request is not None:
            req = catalog.get(access_request)
            if req is None or not req.get("approved") or req.get("expiry") <= now:
                replies.append({"id": rid, "status": "request_unavailable"})
                continue
            has_resources = bool(req.get("resources"))
            if has_resources:
                # Any existing resource request in the chain blocks a new one.
                existing_resource = any(
                    catalog.get(a) and catalog[a].get("resources")
                    for a in active_requests
                )
                if existing_resource:
                    replies.append({"id": rid, "status": "resource_already_active"})
                    continue
            if access_request not in active_requests:
                active_requests.append(access_request)

        # Check that all active requests are still valid (not silently dropped).
        for a in active_requests:
            req = catalog.get(a)
            if req is None or not req.get("approved") or req.get("expiry") <= now:
                replies.append({"id": rid, "status": "request_unavailable"})
                continue

        # Compute roles and resources.
        roles = set(cached_user.get("roles", []))
        resources = set()
        for a in active_requests:
            req = catalog.get(a)
            roles.update(req.get("roles", []))
            resources.update(req.get("resources", []))

        roles = sorted(roles)
        resources = sorted(resources)

        if active_requests:
            expiry = min(now + session_ttl, min(catalog[a]["expiry"] for a in active_requests))
        else:
            expiry = now + session_ttl

        login_time = prev["login_time"]

        new_session = {
            "user": cached_user,
            "login_time": login_time,
            "expiry": expiry,
            "active_requests": active_requests,
        }
        sessions[rid] = new_session
        session_ids.append(rid)

        extensions = cached_user.get("traits", {})
        ssh = _encode_ssh(roles, resources, extensions, login_time, expiry)
        tls = _encode_tls(cached_user.get("name"), sorted(active_requests), login_time, expiry)

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
