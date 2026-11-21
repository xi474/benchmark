def compute(payload):
    """按记录顺序产生 [表名,行号,时间,[租户,主体]]，为跨表归一化保留租户作用域。"""
    result = []
    for rec in payload["records"]:
        result.append([
            rec["table"],
            rec["id"],
            rec["time"],
            [rec["tenant"], rec["subject"]],
        ])
    return result
