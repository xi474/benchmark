def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    return {
        "loss": left["loss"],
        "gradients": left["gradients"],
        "partitions": right["partitions"],
        "events": right["events"],
    }
