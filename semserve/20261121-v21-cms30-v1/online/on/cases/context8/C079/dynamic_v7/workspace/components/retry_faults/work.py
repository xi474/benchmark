def compute(payload):
    """按块标签返回可发生的损坏尝试号，限制在 0 至 max_retries，升序去重。"""
    corrupt_attempts = payload.get("corrupt_attempts") or {}
    max_retries = payload.get("max_retries", 0)
    result = {}
    for label, attempts in corrupt_attempts.items():
        valid = sorted({a for a in attempts if 0 <= a <= max_retries})
        result[label] = valid
    return result
