def compute(payload):
    """按 response 位置记录 [原因,到期时间]；失败优先于陈旧，延迟分别为 2000/1000，正常相应用 null。"""
    raise NotImplementedError
