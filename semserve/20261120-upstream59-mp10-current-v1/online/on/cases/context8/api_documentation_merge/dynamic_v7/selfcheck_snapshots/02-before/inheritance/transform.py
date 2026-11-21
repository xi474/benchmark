import math


def _check_finite(value):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError("non-finite number")
    return value


def _validate(value):
    if isinstance(value, dict):
        for k, v in value.items():
            _validate(k)
            _validate(v)
    elif isinstance(value, list):
        for item in value:
            _validate(item)
    elif isinstance(value, float):
        _check_finite(value)
    return value


def transform(payloads, contract):
    if not isinstance(payloads, list) or not isinstance(contract, dict):
        raise ValueError("bad arguments")
    if "name" not in contract:
        raise ValueError("missing name")
    if "inputs" not in contract or not isinstance(contract["inputs"], list):
        raise ValueError("missing inputs")
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    _validate(payloads)

    payload = payloads[0]
    # If the object has exactly keys name/result, the business input is its result.
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]

    if not isinstance(payload, dict):
        raise ValueError("payload must be object")

    objects = payload.get("objects")
    target = payload.get("target")
    if not isinstance(objects, list):
        raise ValueError("missing objects")
    if not isinstance(target, str):
        raise ValueError("missing target")

    by_id = {}
    for obj in objects:
        if not isinstance(obj, dict) or "id" not in obj:
            raise ValueError("bad object")
        by_id[obj["id"]] = obj

    if target not in by_id:
        raise ValueError("unknown target")

    # Candidate order: target then its mro.
    order = [target] + list(by_id[target].get("mro", []))
    provider = None
    for oid in order:
        obj = by_id.get(oid)
        if obj is None:
            raise ValueError("unknown mro id")
        doc = obj.get("doc")
        if isinstance(doc, str) and doc.strip():
            provider = oid
            break

    if provider is None:
        return {"name": contract["name"], "result": {"provider": None, "namespace": None, "aliases": {}}}

    pobj = by_id[provider]
    namespace = pobj.get("namespace")
    aliases = pobj.get("aliases")
    if not isinstance(aliases, dict):
        aliases = {}

    return {
        "name": contract["name"],
        "result": {
            "provider": provider,
            "namespace": namespace,
            "aliases": aliases,
        },
    }
