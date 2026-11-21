def transform(payloads, contract):
    if len(payloads) != len(contract['inputs']):
        raise ValueError('payload count mismatch')

    sources = ['json', 'csv', 'jsonl']
    # Each payload is the wrapper {"name":..., "result": {"records": [...]}}
    records_by_source = []
    for payload in payloads:
        if not isinstance(payload, dict) or 'result' not in payload:
            raise ValueError('payload must be a component wrapper')
        result = payload['result']
        if not isinstance(result, dict) or 'records' not in result:
            raise ValueError('result must contain records')
        records = result['records']
        if not isinstance(records, list):
            raise ValueError('records must be a list')
        records_by_source.append(records)

    # Merge by id, first present value wins per field (source priority order).
    users = {}
    for source, records in zip(sources, records_by_source):
        for rec in records:
            if not isinstance(rec, dict) or 'id' not in rec:
                raise ValueError('record must be an object with id')
            uid = rec['id']
            if uid not in users:
                users[uid] = {'id': uid}
            for field in ('name', 'email', 'joined'):
                if field in rec and field not in users[uid]:
                    users[uid][field] = rec[field]

    # Conflicts: same field with two or more distinct values across sources.
    field_values = {}
    for source, records in zip(sources, records_by_source):
        for rec in records:
            uid = rec['id']
            for field in ('name', 'email', 'joined'):
                if field in rec:
                    key = (uid, field)
                    field_values.setdefault(key, []).append({'source': source, 'value': rec[field]})

    conflicts = []
    for (uid, field), entries in field_values.items():
        distinct = []
        seen = set()
        for e in entries:
            marker = repr(e['value'])
            if marker not in seen:
                seen.add(marker)
                distinct.append(e)
        if len(distinct) >= 2:
            conflicts.append({'id': uid, 'field': field, 'values': entries})

    conflicts.sort(key=lambda c: (c['id'], c['field']))
    user_list = [users[k] for k in sorted(users.keys())]

    return {'name': contract['name'], 'result': {'users': user_list, 'conflicts': conflicts}}
