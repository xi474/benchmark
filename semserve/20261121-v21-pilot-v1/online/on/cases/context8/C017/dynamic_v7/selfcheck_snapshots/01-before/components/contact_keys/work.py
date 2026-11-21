def compute(payload):
    """保留批次和行序，为每条记录生成清理首尾空白并转小写的邮箱。"""
    return [
        [record["email"].strip().lower() for record in batch]
        for batch in payload["batches"]
    ]
