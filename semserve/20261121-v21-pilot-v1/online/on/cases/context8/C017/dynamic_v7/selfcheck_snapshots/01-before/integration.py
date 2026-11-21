def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    batches = payload["batches"]
    keys = left   # list of batches, each a list of normalized emails
    profiles = right  # list of batches, each a list of {name, city, source, time}

    # Ledger state.
    # records: email -> {"name": str, "city": str, "first_contact": int, "complete": bool}
    records = {}
    # sources: source -> set of emails
    sources = {}

    result_batches = []

    for bi, batch in enumerate(batches):
        emails = keys[bi]
        profs = profiles[bi]

        # Work on a temporary view: snapshot of records and sources.
        tmp_records = {k: dict(v) for k, v in records.items()}
        tmp_sources = {k: set(v) for k, v in sources.items()}

        items = []
        conflict = False

        for i, rec in enumerate(batch):
            email = emails[i]
            p = profs[i]
            name = p["name"]
            city = p["city"]
            source = p["source"]
            time = p["time"]

            existing = tmp_records.get(email)

            if existing is not None and existing["complete"]:
                # Immutable audit fact: duplicate submission.
                # Merge source into derived view.
                tmp_sources.setdefault(source, set()).add(email)
                items.append("duplicate")
                continue

            # Determine candidate name/city for this record.
            if existing is None:
                cand_name = name
                cand_city = city
            else:
                # Non-empty old fields cannot be cleared by empty values.
                cand_name = name if name else existing["name"]
                cand_city = city if city else existing["city"]

            # Conflict check against all existing records (complete or incomplete)
            # with non-empty name/city.
            for other_email, other in tmp_records.items():
                if other_email == email:
                    continue
                if other["name"] and cand_name and other["name"] != cand_name:
                    conflict = True
                    break
                if other["city"] and cand_city and other["city"] != cand_city:
                    conflict = True
                    break
            if conflict:
                break

            # Also check conflict against the candidate's own existing fields.
            if existing is not None:
                if existing["name"] and cand_name and existing["name"] != cand_name:
                    conflict = True
                    break
                if existing["city"] and cand_city and existing["city"] != cand_city:
                    conflict = True
                    break

            # Determine status.
            if existing is None:
                complete = bool(name) and bool(city)
                tmp_records[email] = {
                    "name": name,
                    "city": city,
                    "first_contact": time,
                    "complete": complete,
                }
                tmp_sources.setdefault(source, set()).add(email)
                items.append("accepted" if complete else "incomplete")
            else:
                was_complete = existing["complete"]
                new_name = existing["name"] or name
                new_city = existing["city"] or city
                complete = bool(new_name) and bool(new_city)
                tmp_records[email] = {
                    "name": new_name,
                    "city": new_city,
                    "first_contact": existing["first_contact"],
                    "complete": complete,
                }
                tmp_sources.setdefault(source, set()).add(email)
                if not was_complete and complete:
                    items.append("promoted")
                else:
                    items.append("duplicate")

        if conflict:
            result_batches.append({"status": "rejected", "items": []})
        else:
            records = tmp_records
            sources = tmp_sources
            result_batches.append({"status": "committed", "items": items})

    # Build accepted and incomplete lists.
    accepted = []
    incomplete = []
    for email in sorted(records):
        r = records[email]
        row = {
            "email": email,
            "name": r["name"],
            "city": r["city"],
            "first_contact": r["first_contact"],
            "sources": sorted(s for s, emails in sources.items() if email in emails),
        }
        if r["complete"]:
            accepted.append(row)
        else:
            incomplete.append(row)

    # Build sources view: source -> sorted unique emails.
    sources_view = {s: sorted(emails) for s, emails in sorted(sources.items())}

    return {
        "batches": result_batches,
        "accepted": accepted,
        "incomplete": incomplete,
        "sources": sources_view,
    }
