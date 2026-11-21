import json
import re
from collections import defaultdict
from pathlib import Path

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _norm_name(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def _norm_phone(s):
    return re.sub(r"[^0-9]", "", (s or ""))


def _norm_addr(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _norm_email(s):
    return (s or "").strip().lower()


def _parse_date(s, source):
    s = (s or "").strip()
    if source == "mobile":
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    elif source == "internet":
        m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
        if m:
            return (int(m.group(3)), int(m.group(1)), int(m.group(2)))
    elif source == "cable":
        m = re.match(r"^(\d{4})(\d{2})(\d{2})$", s)
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    elif source == "streaming":
        m = re.match(r"^(\d{2})\s+([A-Za-z]{3})\s+(\d{4})$", s)
        if m:
            mon = MONTHS.get(m.group(2).lower())
            if mon:
                return (int(m.group(3)), mon, int(m.group(1)))
    return None


def _parse_record(rec):
    src = rec["source"]
    f = rec["fields"]
    if src == "mobile":
        first = (f.get("first") or "").strip()
        last = (f.get("last") or "").strip()
        dob = _parse_date(f.get("dob"), src)
        ssn = _norm_phone(f.get("ssn"))
        email = _norm_email(f.get("email"))
        phone = _norm_phone(f.get("phone"))
        addr = _norm_addr(f.get("address"))
    elif src == "internet":
        fn = (f.get("full_name") or "").strip()
        parts = fn.split()
        first = parts[0] if parts else ""
        last = parts[-1] if len(parts) > 1 else ""
        dob = _parse_date(f.get("birth_date"), src)
        ssn = ""
        email = _norm_email(f.get("mail"))
        phone = _norm_phone(f.get("tel"))
        addr = _norm_addr(f.get("street"))
    elif src == "cable":
        lf = (f.get("last_first") or "").strip()
        if "," in lf:
            last, first = lf.split(",", 1)
        else:
            last, first = lf, ""
        last = last.strip()
        first = first.strip()
        dob = _parse_date(f.get("birth"), src)
        gid = _norm_phone(f.get("government_id"))
        ssn = gid
        email = _norm_email(f.get("contact"))
        phone = _norm_phone(f.get("phone"))
        addr = _norm_addr(f.get("location"))
    elif src == "streaming":
        fn = (f.get("customer") or "").strip()
        parts = fn.split()
        first = parts[0] if parts else ""
        last = parts[-1] if len(parts) > 1 else ""
        dob = _parse_date(f.get("date_of_birth"), src)
        ssn = ""
        email = _norm_email(f.get("email"))
        phone = _norm_phone(f.get("telephone"))
        addr = _norm_addr(f.get("address"))
    else:
        first = last = ""
        dob = None
        ssn = email = phone = addr = ""
    return {
        "id": rec["id"],
        "source": src,
        "first": first,
        "last": last,
        "dob": dob,
        "ssn": ssn,
        "email": email,
        "phone": phone,
        "addr": addr,
    }


def _edit1(s):
    if not s:
        return set()
    out = set()
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789.@_-"
    for i in range(len(s) + 1):
        for c in alphabet:
            out.add(s[:i] + c + s[i:])
    for i in range(len(s)):
        out.add(s[:i] + s[i + 1:])
    for i in range(len(s)):
        for c in alphabet:
            out.add(s[:i] + c + s[i + 1:])
    return out


def _email_key(e):
    if "@" in e:
        local, domain = e.split("@", 1)
    else:
        local, domain = e, ""
    return (local, domain)


def _email_similar(a, b):
    if not a or not b:
        return False
    if a == b:
        return True
    la, da = _email_key(a)
    lb, db = _email_key(b)
    if da != db:
        return False
    if abs(len(la) - len(lb)) > 1:
        return False
    if len(la) == len(lb):
        diffs = sum(1 for x, y in zip(la, lb) if x != y)
        return diffs <= 1
    if len(la) > len(lb):
        la, lb = lb, la
    i = j = 0
    skipped = False
    while i < len(la) and j < len(lb):
        if la[i] == lb[j]:
            i += 1
            j += 1
        else:
            if skipped:
                return False
            skipped = True
            j += 1
    return True


def _name_compatible(a_first, a_last, b_first, b_last, ambiguous):
    af = _norm_name(a_first)
    bf = _norm_name(b_first)
    al = _norm_name(a_last)
    bl = _norm_name(b_last)
    if al and bl and al != bl:
        return False
    if not af or not bf:
        return True
    if af == bf:
        return True
    if af in ambiguous or bf in ambiguous:
        return True
    return False


def transform(payload):
    records = payload["records"]
    ambiguous = set(_norm_name(n) for n in payload.get("ambiguous_names", []))
    parsed = [_parse_record(r) for r in records]

    n = len(parsed)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    blocks = defaultdict(list)
    for i, p in enumerate(parsed):
        if p["phone"]:
            blocks[("ph", p["phone"])].append(i)
        if p["addr"]:
            blocks[("ad", p["addr"])].append(i)
        if p["email"]:
            blocks[("em", p["email"])].append(i)
        if p["ssn"] and len(p["ssn"]) == 4:
            blocks[("s4", p["ssn"])].append(i)
        if p["ssn"] and len(p["ssn"]) == 9:
            blocks[("s9", p["ssn"])].append(i)
        if p["dob"] and _norm_name(p["last"]):
            blocks[("dl", (p["dob"], _norm_name(p["last"])))].append(i)

    email_index = defaultdict(list)
    for i, p in enumerate(parsed):
        if p["email"]:
            email_index[p["email"]].append(i)

    def consider(i, j):
        a, b = parsed[i], parsed[j]
        if a["id"] == b["id"]:
            return
        af = _norm_name(a["first"])
        bf = _norm_name(b["first"])
        al = _norm_name(a["last"])
        bl = _norm_name(b["last"])
        # Last names must agree when both present.
        if al and bl and al != bl:
            return
        # Full (non-ambiguous) first names are strong discriminators.
        if af and bf and af != bf and af not in ambiguous and bf not in ambiguous:
            return
        # Strong identifier: 9-digit government id match.
        if a["ssn"] and b["ssn"] and len(a["ssn"]) == 9 and len(b["ssn"]) == 9:
            if a["ssn"] == b["ssn"]:
                union(i, j)
            return
        # 4-digit partial id: must agree with family/name/dob.
        if a["ssn"] and b["ssn"] and len(a["ssn"]) == 4 and len(b["ssn"]) == 4:
            if a["ssn"] != b["ssn"]:
                return
        # Same full first name + same dob is strong.
        if af and bf and af == bf and af not in ambiguous:
            if a["dob"] and b["dob"] and a["dob"] == b["dob"]:
                union(i, j)
                return
        # Same email (exact) + same dob + compatible name.
        if a["email"] and b["email"] and a["email"] == b["email"]:
            if a["dob"] and b["dob"] and a["dob"] == b["dob"]:
                union(i, j)
                return
        # Same phone + same dob + same last name (family members differ by dob).
        if a["phone"] and b["phone"] and a["phone"] == b["phone"]:
            if a["dob"] and b["dob"] and a["dob"] == b["dob"]:
                union(i, j)
                return

    for key, idxs in blocks.items():
        for x in range(len(idxs)):
            for y in range(x + 1, len(idxs)):
                consider(idxs[x], idxs[y])

    all_emails = set(p["email"] for p in parsed if p["email"])
    for i, p in enumerate(parsed):
        if not p["email"]:
            continue
        for variant in _edit1(p["email"]):
            if variant in all_emails and variant != p["email"]:
                for j in email_index[variant]:
                    consider(i, j)

    groups = defaultdict(list)
    for i, p in enumerate(parsed):
        groups[find(i)].append(p["id"])

    clusters = [sorted(g) for g in groups.values()]
    return {"clusters": clusters}


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return value
