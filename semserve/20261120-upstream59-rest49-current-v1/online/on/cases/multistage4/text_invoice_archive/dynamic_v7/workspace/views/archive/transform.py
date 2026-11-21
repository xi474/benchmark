import csv
import io


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {'name', 'result'}:
        return payload['result']
    return payload


def _safe_segment(value):
    if not isinstance(value, str) or value.strip() != value or value == '':
        raise ValueError('invalid path segment')
    if value in ('.', '..'):
        raise ValueError('invalid path segment')
    if '/' in value or '\\' in value or ':' in value:
        raise ValueError('invalid path segment')
    return value


def _safe_relpath(value):
    if not isinstance(value, str):
        raise ValueError('invalid path')
    if value.startswith('/') or '\\' in value or ':' in value:
        raise ValueError('invalid path')
    parts = value.split('/')
    for part in parts:
        if part in ('', '.', '..'):
            raise ValueError('invalid path')
    return value


def transform(payloads, contract):
    if len(payloads) != len(contract['inputs']):
        raise ValueError('payload count mismatch')
    documents = _unwrap(payloads[0])
    classification = _unwrap(payloads[1])
    amounts = _unwrap(payloads[2])

    if not isinstance(documents, dict) or 'documents' not in documents:
        raise ValueError('missing documents')
    docs = documents['documents']
    if not isinstance(docs, list):
        raise ValueError('documents must be list')

    classes = classification.get('classes', {}) if isinstance(classification, dict) else {}
    amts = amounts.get('amounts', {}) if isinstance(amounts, dict) else {}

    archives = []
    rows = []
    totals = {'invoice': 0, 'receipt': 0}

    for doc in docs:
        if not isinstance(doc, dict):
            raise ValueError('document must be object')
        did = doc['id']
        filename = doc['filename']
        text = doc['text']
        if not isinstance(did, str) or not isinstance(filename, str) or not isinstance(text, str):
            raise ValueError('invalid document fields')
        _safe_segment(did)
        _safe_relpath(filename)
        kind = classes.get(did)
        if kind not in ('invoice', 'receipt', 'other'):
            raise ValueError('missing classification')
        amt = amts.get(did)
        if not isinstance(amt, dict):
            raise ValueError('missing amounts')
        total = amt.get('total')
        vat = amt.get('vat')
        if kind in ('invoice', 'receipt') and total is None:
            raise ValueError('invoice/receipt requires total')
        path = f'classified/{kind}/{did}/{filename}'
        hexval = text.encode('utf-8').hex()
        archives.append({'path': path, 'hex': hexval})
        rows.append({'id': did, 'filename': filename, 'kind': kind, 'total': total, 'vat': vat})
        if kind in ('invoice', 'receipt') and total is not None:
            totals[kind] += int(total.replace('.', ''))

    archives.sort(key=lambda x: x['path'])
    rows.sort(key=lambda x: x['id'])

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator='\n')
    writer.writerow(['id', 'filename', 'kind', 'total', 'vat'])
    for r in rows:
        writer.writerow([r['id'], r['filename'], r['kind'], r['total'] if r['total'] is not None else '', r['vat']])
    csv_text = buf.getvalue()

    def fmt(cents):
        return f'{cents // 100}.{cents % 100:02d}'

    result = {
        'archives': archives,
        'rows': rows,
        'csv': csv_text,
        'totals': {'invoice': fmt(totals['invoice']), 'receipt': fmt(totals['receipt'])},
    }
    return {'name': contract['name'], 'result': result}
