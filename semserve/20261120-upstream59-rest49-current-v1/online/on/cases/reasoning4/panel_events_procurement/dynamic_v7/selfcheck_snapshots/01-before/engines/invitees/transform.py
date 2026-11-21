def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _require_str(v, field):
    if not isinstance(v, str) or not v.strip():
        raise ValueError("invalid %s" % field)
    return v


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    payload = payloads[0]
    # If the object has exactly keys name/result, only result is business input.
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    if not isinstance(payload, dict):
        raise ValueError("business input must be object")

    groups = payload.get("groups")
    invite_groups = payload.get("invite_groups")
    exclude = payload.get("exclude")
    namespace = payload.get("namespace")

    if not isinstance(groups, list):
        raise ValueError("groups must be list")
    if not isinstance(invite_groups, list):
        raise ValueError("invite_groups must be list")
    if not isinstance(exclude, list):
        raise ValueError("exclude must be list")
    if not isinstance(namespace, str) or not namespace.strip():
        raise ValueError("namespace must be non-empty string")

    group_map = {}
    for g in groups:
        if not isinstance(g, dict):
            raise ValueError("group must be object")
        gid = _require_str(g.get("id"), "group id")
        members = g.get("members")
        if not isinstance(members, list) or len(members) == 0:
            raise ValueError("group members must be non-empty list")
        for m in members:
            _require_str(m, "member id")
        if gid in group_map:
            raise ValueError("duplicate group id")
        group_map[gid] = members

    exclude_set = set()
    for e in exclude:
        exclude_set.add(_require_str(e, "exclude id"))

    member_set = set()
    for gid in invite_groups:
        gid = _require_str(gid, "invite group id")
        if gid not in group_map:
            raise ValueError("unknown group")
        for m in group_map[gid]:
            member_set.add(m)

    members = sorted(m for m in member_set if m not in exclude_set)
    group_id = namespace + "-panel"

    return {"name": contract["name"], "result": {"members": members, "group_id": group_id}}
