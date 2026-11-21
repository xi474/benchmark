import re
from datetime import datetime

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _alpha_lower(value):
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _digits(value):
    if value is None:
        return ""
    return re.sub(r"[^0-9]", "", str(value))


def _iso_date(value):
    if value is None:
        return ""
    return value


def _normalize(record):
    source = record["source"]
    fields = record["fields"]
    if source == "internet":
        full_name = fields.get("full_name", "")
        parts = full_name.split(" ", 1)
        first = parts[0] if parts else ""
        last = parts[1] if len(parts) > 1 else ""
        dob_raw = fields.get("birth_date", "")
        # MM/DD/YYYY
        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", dob_raw)
        dob = "%04d-%02d-%02d" % (int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else ""
        ssn = ""
        mail = fields.get("mail", "")
        phone = fields.get("tel", "")
        address = fields.get("street", "")
    else:  # streaming
        full_name = fields.get("customer", "")
        parts = full_name.split(" ", 1)
        first = parts[0] if parts else ""
        last = parts[1] if len(parts) > 1 else ""
        dob_raw = fields.get("date_of_birth", "")
        # DD Mon YYYY
        m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})$", dob_raw)
        if m:
            mon = _MONTHS.get(m.group(2).lower())
            dob = "%04d-%02d-%02d" % (int(m.group(3)), mon, int(m.group(1))) if mon else ""
        else:
            dob = ""
        ssn = ""
        mail = fields.get("email", "")
        phone = fields.get("telephone", "")
        address = fields.get("address", "")

    return {
        "id": record["id"],
        "first": _alpha_lower(first),
        "last": _alpha_lower(last),
        "dob": _iso_date(dob),
        "ssn": _digits(ssn),
        "mail": _alpha_lower(mail),
        "phone": _digits(phone),
        "address": _alpha_lower(address),
    }


def compute(payload):
    """标准化 ('internet', 'streaming') 渠道记录，返回 [原位置,字段对象] 数组。"""
    out = []
    for i, record in enumerate(payload["records"]):
        if record["source"] in ("internet", "streaming"):
            out.append([i, _normalize(record)])
    return out
