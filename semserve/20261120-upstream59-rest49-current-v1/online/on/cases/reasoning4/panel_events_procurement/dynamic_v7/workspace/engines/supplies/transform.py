import math


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_finite_number(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def _require_str(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("invalid %s" % field)
    return value


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")

    products = payload.get("products")
    requirements = payload.get("requirements")
    if not isinstance(products, list):
        raise ValueError("products must be list")
    if not isinstance(requirements, list):
        raise ValueError("requirements must be list")

    # Validate products
    product_by_id = {}
    for p in products:
        if not isinstance(p, dict):
            raise ValueError("product must be object")
        pid = _require_str(p.get("id"), "product.id")
        category = _require_str(p.get("category"), "product.category")
        stock = p.get("stock")
        price_cents = p.get("price_cents")
        rating = p.get("rating")
        if not _is_int(stock) or stock < 0:
            raise ValueError("invalid stock")
        if not _is_int(price_cents) or price_cents < 0:
            raise ValueError("invalid price_cents")
        if not _is_int(rating) or rating < 0:
            raise ValueError("invalid rating")
        if pid in product_by_id:
            raise ValueError("duplicate product id")
        product_by_id[pid] = {
            "id": pid,
            "category": category,
            "stock": stock,
            "price_cents": price_cents,
            "rating": rating,
        }

    # Validate requirements: each category only one requirement
    seen_categories = set()
    req_by_category = {}
    for r in requirements:
        if not isinstance(r, dict):
            raise ValueError("requirement must be object")
        category = _require_str(r.get("category"), "requirement.category")
        quantity = r.get("quantity")
        if not _is_int(quantity) or quantity < 1:
            raise ValueError("invalid quantity")
        if category in seen_categories:
            raise ValueError("duplicate requirement category")
        seen_categories.add(category)
        req_by_category[category] = quantity

    items = []
    unavailable = []

    for category in sorted(req_by_category):
        quantity = req_by_category[category]
        candidates = [p for p in product_by_id.values() if p["category"] == category and p["stock"] >= quantity]
        if not candidates:
            unavailable.append(category)
            continue
        # rating max, then price_cents min, then id min
        best = min(candidates, key=lambda p: (-p["rating"], p["price_cents"], p["id"]))
        items.append({
            "category": category,
            "id": best["id"],
            "quantity": quantity,
            "total_cents": best["price_cents"] * quantity,
        })

    items.sort(key=lambda x: x["category"])
    unavailable.sort()

    return {"name": contract["name"], "result": {"items": items, "unavailable": unavailable}}
