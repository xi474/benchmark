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

    amounts = {}
    for doc in docs:
        if not isinstance(doc, dict):
            raise ValueError("document must be object")
        _check_finite(doc)
        if "id" not in doc or "text" not in doc:
            raise ValueError("document missing id/text")
        doc_id = doc["id"]
        if not isinstance(doc_id, str) or not doc_id.strip():
            raise ValueError("invalid id")
        text = doc["text"]
        if not isinstance(text, str):
            raise ValueError("text must be string")
        total = None
        vat = "0.00"
        seen_total = False
        seen_amount_due = False
        seen_vat = False
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            low = line.lower()
            if low.startswith("total:"):
                value = _parse_amount(line[len("total:"):].strip())
                if seen_total:
                    raise ValueError("duplicate Total")
                seen_total = True
                total = value
            elif low.startswith("amount due:"):
                value = _parse_amount(line[len("amount due:"):].strip())
                if seen_amount_due:
                    raise ValueError("duplicate Amount Due")
                seen_amount_due = True
                if total is None:
                    total = value
            elif low.startswith("vat:"):
                value = _parse_amount(line[len("vat:"):].strip())
                if seen_vat:
                    raise ValueError("duplicate VAT")
                seen_vat = True
                vat = value
        amounts[doc_id] = {"total": total, "vat": vat}

    return {"name": contract["name"], "result": {"amounts": amounts}}


_AMOUNT_RE = re.compile(r"^(?:USD\s+)?(\d{1,3}(?:,\d{3})*|\d+)\.(\d{2})$")


def _parse_amount(s):
    s = s.strip()
    m = _AMOUNT_RE.match(s)
    if not m:
        raise ValueError("invalid amount: %r" % s)
    int_part = m.group(1).replace(",", "")
    frac = m.group(2)
    return "%s.%s" % (int_part, frac)
