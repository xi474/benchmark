def compute(payload):
    """按记录顺序产生 [表名,行号,时间,[租户,主体]]，为跨表归一化保留租户作用域。"""
    return [
        [r["table"], r["id"], r["time"], [r["tenant"], r["subject"]]]
        for r in payload["records"]
    ]
