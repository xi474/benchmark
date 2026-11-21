def compute(payload):
    """按输入顺序重放策略变更，为每个 request 原位置生成授权布尔值。"""
    policies = payload.get("policies", {})
    events = payload.get("events", [])

    # 当前每个 user 的允许规则列表（policy 事件会整体替换）。
    allow = {user: list(rules) for user, rules in policies.items()}

    result = {}
    for idx, event in enumerate(events):
        op = event.get("op")
        if op == "policy":
            user = event.get("user")
            allow[user] = list(event.get("allow", []))
        elif op == "request":
            user = event.get("user")
            cluster = event.get("cluster")
            verb = event.get("verb")
            service = event.get("service")
            rules = allow.get(user, [])
            authorized = False
            for rule in rules:
                if rule.get("cluster") != cluster or rule.get("verb") != verb:
                    continue
                rule_service = rule.get("service")
                if rule_service is None or rule_service == "*" or rule_service == service:
                    authorized = True
                    break
            result[str(idx)] = authorized
    return result
