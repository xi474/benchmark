def compute(payload):
    """保留批次和行序，返回 name,city,source,time 对象；姓名与城市的空白折叠为单个空格。"""
    result = []
    for batch in payload["batches"]:
        rows = []
        for rec in batch:
            rows.append({
                "name": " ".join(rec["name"].split()),
                "city": " ".join(rec["city"].split()),
                "source": rec["source"],
                "time": rec["time"],
            })
        result.append(rows)
    return result
