def _clean(text):
    # collapse internal whitespace, strip leading/trailing whitespace and
    # slash/comma/colon/semicolon; periods are preserved.
    parts = text.split()
    s = " ".join(parts)
    s = s.strip(" \t\r\n/:,;")
    return s


def _join_subfields(field, codes):
    parts = []
    for sf in field.get("subfields", []):
        if sf.get("code") in codes:
            parts.append(sf.get("value", ""))
    return _clean(" ".join(parts))


def _parse_link(value):
    # $6 value like "880-01" or "100-01/..." -> (tag, nn)
    v = value.strip()
    if "/" in v:
        v = v.split("/", 1)[0]
    if "-" not in v:
        return None
    tag, nn = v.split("-", 1)
    if not tag or not nn:
        return None
    return tag, nn


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    src = payloads[0]
    # When input object has exactly keys name/result, only result is business input.
    if isinstance(src, dict) and set(src.keys()) == {"name", "result"}:
        src = src["result"]

    records = src["records"]

    out_records = []
    for rec in records:
        rid = rec["id"]
        fields = rec.get("fields", [])

        authors = []
        titles = []
        # map (tag, nn) -> alternate text
        alt_map = {}

        for f in fields:
            tag = f.get("tag")
            sf6 = None
            for sf in f.get("subfields", []):
                if sf.get("code") == "6":
                    sf6 = sf.get("value", "")
                    break
            if tag == "880":
                link = _parse_link(sf6) if sf6 else None
                if link is not None:
                    ltag, nn = link
                    if ltag in ("100", "245"):
                        alt_map[(ltag, nn)] = _join_subfields(f, ("a", "b"))
            elif tag in ("100", "245"):
                link = _parse_link(sf6) if sf6 else None
                if link is not None:
                    ltag, nn = link
                    if ltag == "880":
                        alt_map[(tag, nn)] = _join_subfields(f, ("a", "b"))

        for f in fields:
            tag = f.get("tag")
            if tag == "100":
                name = _join_subfields(f, ("a", "b"))
                sf6 = None
                for sf in f.get("subfields", []):
                    if sf.get("code") == "6":
                        sf6 = sf.get("value", "")
                        break
                link = _parse_link(sf6) if sf6 else None
                alternates = []
                if link is not None and link[0] == "880":
                    alt = alt_map.get(("100", link[1]))
                    if alt is not None and alt != name:
                        alternates.append(alt)
                alternates = sorted(set(alternates))
                authors.append({"name": name, "alternates": alternates})
            elif tag == "245":
                title = _join_subfields(f, ("a", "b"))
                sf6 = None
                for sf in f.get("subfields", []):
                    if sf.get("code") == "6":
                        sf6 = sf.get("value", "")
                        break
                link = _parse_link(sf6) if sf6 else None
                alternates = []
                if link is not None and link[0] == "880":
                    alt = alt_map.get(("245", link[1]))
                    if alt is not None and alt != title:
                        alternates.append(alt)
                alternates = sorted(set(alternates))
                titles.append({"title": title, "alternates": alternates})

        out_records.append(
            {"id": rid, "authors": authors, "titles": titles}
        )

    return {"name": contract["name"], "result": {"records": out_records}}
