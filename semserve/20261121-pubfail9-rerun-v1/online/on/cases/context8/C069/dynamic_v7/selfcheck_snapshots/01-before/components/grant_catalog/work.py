def compute(payload):
    """生成授权条目的有效条件和有序角色/资源集合。以原授权 ID 为键，每项含 approved、expiry、roles、resources。"""
    access_requests = payload.get("access_requests", {})
    result = {}
    for rid, req in access_requests.items():
        roles = sorted(req.get("roles") or [])
        resources = sorted(req.get("resources") or [])
        result[rid] = {
            "approved": req.get("approved", False),
            "expiry": req.get("expiry"),
            "roles": roles,
            "resources": resources,
        }
    return result
