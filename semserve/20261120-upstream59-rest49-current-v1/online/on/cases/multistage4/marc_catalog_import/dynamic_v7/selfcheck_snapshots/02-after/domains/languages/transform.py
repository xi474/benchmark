def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    raw_input = payloads[0]
    records_payload = payloads[1]

    # Unwrap name/result envelope when present.
    if isinstance(raw_input, dict) and set(raw_input) == {"name", "result"}:
        raw_input = raw_input["result"]
    if isinstance(records_payload, dict) and set(records_payload) == {"name", "result"}:
        records_payload = records_payload["result"]

    language_codes = raw_input["language_codes"]
    valid = set()
    for code in language_codes:
        if not isinstance(code, str) or len(code) != 3 or not code.isalpha() or not code.islower():
            raise ValueError("invalid language code")
        valid.add(code)

    records = records_payload["records"]
    out_records = []
    for rec in records:
        rid = rec["id"]
        controls = rec["controls"]
        fields = rec["fields"]

        codes = set()

        # 008 controlfield: positions 35..37 (0-indexed).
        if "008" in controls:
            c008 = controls["008"]
            if len(c008) < 38:
                raise ValueError("008 too short")
            code = c008[35:38]
            if code in valid:
                codes.add(code)

        # 041 datafields: $a/$d/$h.
        for f in fields:
            if f["tag"] != "041":
                continue
            for sf in f["subfields"]:
                if sf["code"] not in ("a", "d", "h"):
                    continue
                text = sf["value"].strip()
                if len(text) % 3 != 0:
                    raise ValueError("041 code length not multiple of 3")
                for i in range(0, len(text), 3):
                    code = text[i:i + 3]
                    if code in valid:
                        codes.add(code)

        out_records.append({"id": rid, "languages": sorted(codes)})

    return {"name": contract["name"], "result": {"records": out_records}}
