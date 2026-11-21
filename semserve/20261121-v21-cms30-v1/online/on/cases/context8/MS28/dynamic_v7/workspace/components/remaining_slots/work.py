def compute(payload):
    """每个撤回情景返回仍可用的时段映射，时段 ID 对应 [时刻,容量]。"""
    slots = payload["slots"]
    withdrawals = payload["withdrawals"]
    slot_map = {slot_id: [day, capacity] for slot_id, day, capacity in slots}
    result = []
    for withdrawn in withdrawals:
        removed = set(withdrawn)
        result.append({sid: slot_map[sid] for sid in slot_map if sid not in removed})
    return result
