def compute(payload):
    """每个 host/stream 返回各次循环读取的 [items,数量,总和] 列表，保持原顺序。"""
    feeds = payload["feeds"]
    result = {}
    for host, streams in feeds.items():
        result[host] = {}
        for stream, batches in streams.items():
            result[host][stream] = [
                [list(batch), len(batch), sum(batch)] for batch in batches
            ]
    return result
