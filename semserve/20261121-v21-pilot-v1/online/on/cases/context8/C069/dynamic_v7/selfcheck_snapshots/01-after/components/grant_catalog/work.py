def compute(payload):
    """生成授权条目的有效条件和有序角色/资源集合。以原授权 ID 为键，每项含 approved、expiry、roles、resources。"""
    access_requests = payload.get("access_requests", {})
    result = {}
    for request_id, request in access_requests.items():
        roles = sorted(request.get("roles", []))
        resources = sorted(request.get("resources", []))
        result[request_id] = {
            "approved": request.get("approved", False),
            "expiry": request.get("expiry"),
            "roles": roles,
            "resources": resources,
        }
    return result
