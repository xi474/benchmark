def compute(payload):
    """返回每辆车可使用的司机 ID 数组，保留司机声明顺序。"""
    vehicles = payload["vehicles"]
    drivers = payload["drivers"]
    result = {}
    for vehicle in vehicles:
        vtype = vehicle["type"]
        usable = [d["id"] for d in drivers if vtype in d["types"]]
        result[vehicle["id"]] = usable
    return result
