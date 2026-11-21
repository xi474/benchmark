def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    batches = payload["batches"]
    keys = left   # list of batches, each a list of normalized emails
    profiles = right  # list of batches, each a list of {name, city, source, time}

    # Ledger state keyed by normalized email.
    # record: {"name": str, "city": str, "first_contact": int, "complete": bool}
    records = {}
    # sources: source -> set of emails (valid records)
    sources = {}

    batch_results = []

    for bi, batch in enumerate(batches):
        emails = keys[bi]
        profs = profiles[bi]

        # Work on a temporary view: snapshot of records and sources.
        tmp_records = {k: dict(v) for k, v in records.items()}
        tmp_sources = {k: set(v) for k, v in sources.items()}

        items = []
        conflict = False

        for ri in range(len(batch)):
            email = emails[ri]
            p = profs[ri]
            name = p["name"]
            city = p["city"]
            source = p["source"]
            time = p["time"]

            existing = tmp_records.get(email)

            if existing is not None:
                # Check conflict against non-empty fields.
                if name and existing["name"] and name != existing["name"]:
                    conflict = True
                    break
                if city and existing["city"] and city != existing["city"]:
                    conflict = True
                    break

                if existing["complete"]:
                    # Immutable audit fact: duplicate.
                    items.append("duplicate")
                else:
                    # Merge non-empty fields; never clear non-empty old fields.
                    if name and not existing["name"]:
                        existing["name"] = name
                    if city and not existing["city"]:
                        existing["city"] = city
                    # first_contact preserved (earliest).
                    if existing["name"] and existing["city"]:
                        existing["complete"] = True
                        items.append("promoted")
                    else:
                        items.append("incomplete")
            else:
                # New record.
                rec = {
                    "name": name,
                    "city": city,
                    "first_contact": time,
                    "complete": bool(name and city),
                }
                tmp_records[email] = rec
                items.append("accepted" if rec["complete"] else "incomplete")

            # Merge source view.
            tmp_sources.setdefault(source, set()).add(email)

        if conflict:
            batch_results.append({"status": "rejected", "items": []})
            continue

        # Commit the temporary view.
        records = tmp_records
        sources = tmp_sources
        batch_results.append({"status": "committed", "items": items})

    # Build final accepted/incomplete lists.
    accepted = []
    incomplete = []
    for email in sorted(records):
        rec = records[email]
        row = {
            "email": email,
            "name": rec["name"],
            "city": rec["city"],
            "first_contact": rec["first_contact"],
            "sources": sorted(s for s in sources if email in sources[s]),
        }
        if rec["complete"]:
            accepted.append(row)
        else:
            incomplete.append(row)

    sources_out = {s: sorted(emails) for s, emails in sorted(sources.items())}

    return {
        "batches": batch_results,
        "accepted": accepted,
        "incomplete": incomplete,
        "sources": sources_out,
    }
