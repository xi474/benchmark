import re
from datetime import datetime


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
    return str(value)


def compute(payload):
    """标准化 ('mobile', 'cable') 渠道记录，返回 [原位置,字段对象] 数组。"""
    out = []
    for index, record in enumerate(payload["records"]):
        source = record["source"]
        fields = record["fields"]
        if source == "mobile":
            first = _alpha_lower(fields.get("first"))
            last = _alpha_lower(fields.get("last"))
            dob = _iso_date(fields.get("dob"))
            ssn = _digits(fields.get("ssn"))
            mail = _alpha_lower(fields.get("email"))
            phone = _digits(fields.get("phone"))
            address = _alpha_lower(fields.get("address"))
        elif source == "cable":
            last_first = fields.get("last_first", "")
            if "," in last_first:
                last, first = last_first.split(",", 1)
            else:
                last, first = last_first, ""
            first = _alpha_lower(first)
            last = _alpha_lower(last)
            birth = fields.get("birth", "")
            if len(birth) == 8:
                dob = "%s-%s-%s" % (birth[0:4], birth[4:6], birth[6:8])
            else:
                dob = _iso_date(birth)
            ssn = _digits(fields.get("government_id"))
            mail = _alpha_lower(fields.get("contact"))
            phone = _digits(fields.get("phone"))
            address = _alpha_lower(fields.get("location"))
        else:
            continue
        obj = {
            "id": record["id"],
            "first": first,
            "last": last,
            "dob": dob,
            "ssn": ssn,
            "mail": mail,
            "phone": phone,
            "address": address,
        }
        out.append([index, obj])
    return out
