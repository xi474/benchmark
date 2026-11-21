import re


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    documents = payloads[0]
    if isinstance(documents, dict) and set(documents) == {"name", "result"}:
        documents = documents["result"]
    docs = documents["documents"]

    amounts = {}
    for doc in docs:
        doc_id = doc["id"]
        text = doc["text"]
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
