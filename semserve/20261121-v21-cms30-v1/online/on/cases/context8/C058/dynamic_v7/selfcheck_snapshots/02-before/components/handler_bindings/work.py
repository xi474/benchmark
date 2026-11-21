STAGES = ("pre", "roles", "includes", "tasks", "post")


def _is_block(item):
    return isinstance(item, dict) and "block" in item


def _is_task(item):
    return isinstance(item, dict) and "id" in item


def compute(payload):
    """输出 [处理器声明顺序映射,叶节点到通知清单的映射]。

    叶节点按同一树位置编码；通知名去重并按声明顺序排列，含 rescue、always。
    """
    handlers = payload.get("handlers", [])
    program = payload.get("program", {})

    handler_order = {name: idx for idx, name in enumerate(handlers)}

    leaf_to_notify = {}

    for stage_idx, stage_name in enumerate(STAGES):
        items = program.get(stage_name, [])
        if not isinstance(items, list):
            continue
        for item_idx, item in enumerate(items):
            if _is_task(item):
                path = "%d/%d" % (stage_idx, item_idx)
                notify = item.get("notify", [])
                if notify:
                    leaf_to_notify[path] = _ordered_notify(notify, handler_order)
            elif _is_block(item):
                block = item["block"]
                for branch_idx, branch_name in enumerate(("tasks", "rescue", "always")):
                    branch = block.get(branch_name, [])
                    if not isinstance(branch, list):
                        continue
                    for task_idx, task in enumerate(branch):
                        if not _is_task(task):
                            continue
                        path = "%d/%d/%d/%d" % (stage_idx, item_idx, branch_idx, task_idx)
                        notify = task.get("notify", [])
                        if notify:
                            leaf_to_notify[path] = _ordered_notify(notify, handler_order)

    return [handler_order, leaf_to_notify]


def _ordered_notify(notify, handler_order):
    seen = set()
    result = []
    for name in notify:
        if name in seen:
            continue
        seen.add(name)
        result.append(name)
    result.sort(key=lambda n: handler_order.get(n, len(handler_order)))
    return result
