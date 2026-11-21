def compute(payload):
    """对每个 complete 事件按原始位置记录 [正常完成事件名,新 revision 或 null]。

    取消与关闭优先级由整合逻辑决定，这里只记录正常完成的效果：
    changed=true 时事件名为 snapshot_updated 且新 revision 为事件中的 revision；
    changed=false 时事件名为 poll_unchanged 且新 revision 为 null。
    """
    result = {}
    for index, event in enumerate(payload.get("events", [])):
        if event.get("op") != "complete":
            continue
        changed = bool(event.get("changed", False))
        if changed:
            name = "snapshot_updated"
            revision = event.get("revision")
        else:
            name = "poll_unchanged"
            revision = None
        result[str(index)] = [name, revision]
    return result
