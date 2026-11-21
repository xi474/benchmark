def compute(payload):
    """按服务 ID 索引门槛及直接输入，值为 [need,inputs]；保留输入顺序和共享故障域。"""
    return {s["id"]: [s["need"], list(s["inputs"])] for s in payload["services"]}
