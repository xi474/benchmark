import math
import re


def _check_finite(value):
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("non-finite number")
    elif isinstance(value, dict):
        for v in value.values():
            _check_finite(v)
    elif isinstance(value, list):
        for v in value:
            _check_finite(v)


def _business_input(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    documents = _business_input(payloads[0])
    if not isinstance(documents, dict) or "documents" not in documents:
        raise ValueError("missing documents")
    _check_finite(documents)
    docs = documents["documents"]
    if not isinstance(docs, list):
        raise ValueError("documents must be a list")

    classes = {}
    seen_ids = set()
    for doc in docs:
        if not isinstance(doc, dict):
            raise ValueError("document must be object")
        _check_finite(doc)
        if "id" not in doc or "text" not in doc:
            raise ValueError("document missing id/text")
        doc_id = doc["id"]
        if not isinstance(doc_id, str) or not doc_id.strip():
            raise ValueError("invalid id")
        if doc_id in seen_ids:
            raise ValueError("duplicate id")
        seen_ids.add(doc_id)
        text = doc["text"]
        if not isinstance(text, str):
            raise ValueError("text must be string")
        words = set(re.findall(r"[A-Za-z]+", text.lower()))
        if "invoice" in words:
            kind = "invoice"
        elif "receipt" in words:
            kind = "receipt"
        else:
            kind = "other"
        classes[doc_id] = kind

    return {"name": contract["name"], "result": {"classes": classes}}
