"""Implement the public business contract in TASK.md."""

import base64
import json


def _b64url(obj):
    raw = json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _encode_ssh(roles, resources, traits, login_time, expires):
    obj = {
        "roles": sorted(roles),
        "allowed_resources": sorted(resources),
        "extensions": traits,
        "login_time": login_time,
        "expires": expires,
    }
    return "SSH-MODEL1." + _b64url(obj)


def _encode_tls(user_name, active_requests, login_time, expires):
    obj = {
        "user": user_name,
        "active_requests": sorted(active_requests),
        "login_time": login_time,
        "expires": expires,
    }
    return "TLS-MODEL1." + _b64url(obj)


def transform(payload):
    user = payload["user"]
    start_time = payload["start_time"]
    session_ttl = payload["session_ttl"]
    access_requests = payload["access_requests"]
    events = payload["events"]

    initial_id = payload.get("initial_id", "s0")

    # Backend user state (mutated by update_user).
    backend_user = {
        "name": user["name"],
        "roles": list(user["roles"]),
        "traits": dict(user["traits"]),
    }

    # Session state.
    sessions = {}
    sessions[initial_id] = {
        "login_time": start_time,
        "expiry": start_time + session_ttl,
        "cached_user": {
            "name": backend_user["name"],
            "roles": list(backend_user["roles"]),
            "traits": dict(backend_user["traits"]),
        },
        "active_requests": {},  # request_id -> request dict
    }

    session_ids = [initial_id]
    replies = []

    for event in events:
        op = event["op"]
        if op == "update_user":
            if "roles" in event:
                backend_user["roles"] = list(event["roles"])
            if "traits" in event:
                backend_user["traits"] = dict(event["traits"])
            continue

        if op == "renew":
            rid = event["id"]
            now = event["time"]
            prev_id = event["prev"]

            if prev_id not in sessions:
                replies.append({"id": rid, "status": "expired"})
                continue

            prev = sessions[prev_id]
            if prev["expiry"] <= now:
                replies.append({"id": rid, "status": "expired"})
                continue

            # Determine cached user.
            if event.get("reload_user"):
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

            # Active requests carried forward.
            active_requests = {k: dict(v) for k, v in prev["active_requests"].items()}

            if event.get("switchback"):
                active_requests = {}

            if "access_request" in event:
                req_id = event["access_request"]
                req = access_requests.get(req_id)
                if req is None or not req.get("approved") or req.get("expiry", 0) <= now:
                    replies.append({"id": rid, "status": "request_unavailable"})
                    continue

                has_resources = bool(req.get("resources"))
                if has_resources:
                    # Any existing resource request in the chain blocks.
                    if any(a.get("resources") for a in active_requests.values()):
                        replies.append({"id": rid, "status": "resource_already_active"})
                        continue
                active_requests[req_id] = dict(req)

            # Expire requests that are no longer valid.
            expired = [k for k, v in active_requests.items() if v.get("expiry", 0) <= now]
            if expired:
                replies.append({"id": rid, "status": "request_unavailable"})
                continue

            # Compute roles and resources.
            roles = set(cached_user["roles"])
            resources = set()
            for req in active_requests.values():
                roles.update(req.get("roles", []))
                resources.update(req.get("resources", []))

            # Compute expiry.
            if active_requests:
                expiry = min(now + session_ttl, min(v["expiry"] for v in active_requests.values()))
            else:
                expiry = now + session_ttl

            new_session = {
                "login_time": prev["login_time"],
                "expiry": expiry,
                "cached_user": cached_user,
                "active_requests": active_requests,
            }
            sessions[rid] = new_session
            session_ids.append(rid)

            ssh = _encode_ssh(
                roles, resources, cached_user["traits"], prev["login_time"], expiry
            )
            tls = _encode_tls(
                cached_user["name"], list(active_requests.keys()), prev["login_time"], expiry
            )
            replies.append(
                {
                    "id": rid,
                    "status": "ok",
                    "ssh_certificate": ssh,
                    "tls_certificate": tls,
                }
            )

    return {"replies": replies, "session_ids": session_ids}


def load_payload(input_path):
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_component(input_path, output_path):
    payload = load_payload(input_path)
    result = transform(payload)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return result
