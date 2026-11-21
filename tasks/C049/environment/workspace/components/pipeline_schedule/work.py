def compute(payload):
    """输出 partitions 和 AFAB 的 events；层边界为 floor(n*r/world)，保留正序前向、逆序反向及跨 stage 发送。"""
    raise NotImplementedError
