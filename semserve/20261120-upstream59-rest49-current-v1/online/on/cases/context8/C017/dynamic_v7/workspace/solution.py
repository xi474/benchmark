from pathlib import Path
import json


def _norm_email(email):
    return email.strip().lower()


def _norm_field(value):
    # compress consecutive whitespace
    return " ".join(value.split())


def transform(payload):
    batches = payload["batches"]

    # records keyed by normalized email
    # each record: {"name": str, "city": str, "first_contact": int, "sources": set}
    records = {}
    # source -> set of emails
    sources = {}

    batch_results = []

    for batch in batches:
        # process into a temporary view (copy of records and sources)
        tmp_records = {k: dict(v, sources=set(v["sources"])) for k, v in records.items()}
        tmp_sources = {k: set(v) for k, v in sources.items()}

        items = []
        conflict = False

        for ev in batch:
            email = _norm_email(ev["email"])
            name = _norm_field(ev.get("name", "") or "")
            city = _norm_field(ev.get("city", "") or "")
            source = ev["source"]
            time = ev["time"]

            rec = tmp_records.get(email)

            if rec is None:
                # new record
                rec = {
                    "name": name,
                    "city": city,
                    "first_contact": time,
                    "sources": set(),
                }
                tmp_records[email] = rec
                if name and city:
                    items.append("accepted")
                else:
                    items.append("incomplete")
            else:
                # existing record: check conflict on non-empty fields
                if name and rec["name"] and name != rec["name"]:
                    conflict = True
                    break
                if city and rec["city"] and city != rec["city"]:
                    conflict = True
                    break

                was_complete = bool(rec["name"] and rec["city"])

                # merge non-empty fields (never clear old non-empty with empty)
                if name and not rec["name"]:
                    rec["name"] = name
                if city and not rec["city"]:
                    rec["city"] = city

                # after merge, check completeness
                if rec["name"] and rec["city"]:
                    if not was_complete:
                        items.append("promoted")
                    else:
                        items.append("duplicate")
                else:
                    items.append("duplicate")

            # add source
            rec["sources"].add(source)
            tmp_sources.setdefault(source, set()).add(email)

        if conflict:
            batch_results.append({"status": "rejected", "items": []})
            continue

        # commit
        records = tmp_records
        sources = tmp_sources
        batch_results.append({"status": "committed", "items": items})

    accepted = []
    incomplete = []
    for email in sorted(records):
        rec = records[email]
        row = {
            "email": email,
            "name": rec["name"],
            "city": rec["city"],
            "first_contact": rec["first_contact"],
            "sources": sorted(rec["sources"]),
        }
        if rec["name"] and rec["city"]:
            accepted.append(row)
        else:
            incomplete.append(row)

    sources_out = {
        k: sorted(v) for k, v in sorted(sources.items())
    }

    return {
        "batches": batch_results,
        "accepted": accepted,
        "incomplete": incomplete,
        "sources": sources_out,
    }


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return value
