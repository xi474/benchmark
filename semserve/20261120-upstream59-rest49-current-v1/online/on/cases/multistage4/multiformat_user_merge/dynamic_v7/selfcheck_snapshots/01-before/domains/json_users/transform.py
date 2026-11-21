import json
from datetime import datetime


def _parse_joined(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError('joined must be string')
    s = value.strip()
    if s == '':
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    raise ValueError('invalid joined date')


def _resolve_id(obj):
    if 'id' in obj:
        raw = obj['id']
    elif 'user_id' in obj:
        raw = obj['user_id']
    else:
        raise ValueError('missing id')
    if isinstance(raw, bool):
        raise ValueError('id must not be bool')
    if isinstance(raw, int):
        return str(raw)
    if isinstance(raw, str):
        s = raw.strip()
        if s == '':
            raise ValueError('id must be non-empty')
        return s
    raise ValueError('id must be str or int')


def _field_value(obj, primary, alias):
    if primary in obj:
        return obj[primary]
    if alias in obj:
        return obj[alias]
    return None


def _normalize_record(obj):
    uid = _resolve_id(obj)
    name = _field_value(obj, 'name', 'full_name')
    email = _field_value(obj, 'email', 'mail')
    joined = _field_value(obj, 'joined', 'joined_at')
    if joined is not None:
        joined = _parse_joined(joined)
    return uid, name, email, joined


def transform(payloads, contract):
    if len(payloads) != len(contract['inputs']):
        raise ValueError('payload count mismatch')
    payload = payloads[0]
    if not isinstance(payload, dict):
        raise ValueError('payload must be object')
    if 'json_text' not in payload:
        raise ValueError('missing json_text')
    text = payload['json_text']
    if not isinstance(text, str):
        raise ValueError('json_text must be string')
    arr = json.loads(text, parse_constant=lambda s: (_ for _ in ()).throw(ValueError('non-finite number')))
    if not isinstance(arr, list):
        raise ValueError('json_text must be an array')

    merged = {}
    for obj in arr:
        if not isinstance(obj, dict):
            raise ValueError('array elements must be objects')
        uid, name, email, joined = _normalize_record(obj)
        rec = merged.get(uid)
        if rec is None:
            rec = {'id': uid}
            merged[uid] = rec
        if name is not None:
            rec['name'] = name
        if email is not None:
            rec['email'] = email
        if joined is not None:
            rec['joined'] = joined

    records = [merged[k] for k in sorted(merged.keys())]
    return {'name': contract['name'], 'result': {'records': records}}
