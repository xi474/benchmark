import math


def compute(payload):
    """输出 partitions 和 AFAB 的 events；层边界为 floor(n*r/world)，保留正序前向、逆序反向及跨 stage 发送。"""
    layers = payload["layers"]
    world_size = payload["world_size"]
    microbatches = payload["microbatches"]

    L = len(layers)
    num_microbatches = len(microbatches)

    partitions = []
    for r in range(world_size):
        start = math.floor(L * r / world_size)
        stop = math.floor(L * (r + 1) / world_size)
        partitions.append({"stage": r, "start": start, "stop": stop})

    events = []

    # Forward: each microbatch passes through all stages in order.
    for m in range(num_microbatches):
        for s in range(world_size):
            events.append({"kind": "forward", "microbatch": m, "stage": s})
            if s < world_size - 1:
                events.append({"kind": "send_activation", "source": s, "target": s + 1})

    # Backward: reverse microbatch order, reverse stage order.
    for m in range(num_microbatches - 1, -1, -1):
        for s in range(world_size - 1, -1, -1):
            events.append({"kind": "backward", "microbatch": m, "stage": s})
            if s > 0:
                events.append({"kind": "send_gradient", "source": s, "target": s - 1})

    return {"partitions": partitions, "events": events}
