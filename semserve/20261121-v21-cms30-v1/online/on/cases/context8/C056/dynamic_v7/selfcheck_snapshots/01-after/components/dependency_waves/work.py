def compute(payload):
    """返回各依赖批次，每批含按 ID 升序排列的任务 ID。同批共享同一事实快照。"""
    tasks = payload["tasks"]
    by_id = {t["id"]: t for t in tasks}
    remaining = set(by_id)
    waves = []
    while remaining:
        ready = sorted(
            tid for tid in remaining
            if all(n not in remaining for n in by_id[tid]["needs"])
        )
        waves.append(ready)
        remaining.difference_update(ready)
    return waves
