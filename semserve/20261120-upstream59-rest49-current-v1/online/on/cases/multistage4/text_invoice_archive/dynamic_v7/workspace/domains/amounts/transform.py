import re

_AMOUNT_RE = re.compile(r'^\s*(?:USD\s+)?(\d{1,3}(?:,\d{3})*|\d+)\.(\d{2})\s*$', re.IGNORECASE)


def _parse_amount(text):
    m = _AMOUNT_RE.match(text)
    if not m:
        raise ValueError('invalid amount')
    int_part = m.group(1).replace(',', '')
    frac = m.group(2)
    return f'{int_part}.{frac}'


def transform(payloads, contract):
    if len(payloads) != len(contract['inputs']):
        raise ValueError('payload count mismatch')
    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {'name', 'result'}:
        payload = payload['result']
    if not isinstance(payload, dict) or 'documents' not in payload:
        raise ValueError('missing documents')
    documents = payload['documents']
    if not isinstance(documents, list):
        raise ValueError('documents must be list')
    amounts = {}
    seen = set()
    for doc in documents:
        if not isinstance(doc, dict):
            raise ValueError('document must be object')
        if 'id' not in doc or 'text' not in doc:
            raise ValueError('missing id/text')
        did = doc['id']
        if not isinstance(did, str):
            raise ValueError('id must be string')
        if did in seen:
            raise ValueError('duplicate id')
        seen.add(did)
        text = doc['text']
        if not isinstance(text, str):
            raise ValueError('text must be string')
        total = None
        vat = None
        for line in text.splitlines():
            stripped = line.strip()
            low = stripped.lower()
            if low.startswith('total:'):
                if total is not None:
                    raise ValueError('duplicate total')
                total = _parse_amount(stripped[len('total:'):])
            elif low.startswith('amount due:'):
                if total is not None:
                    raise ValueError('duplicate total')
                total = _parse_amount(stripped[len('amount due:'):])
            elif low.startswith('vat:'):
                if vat is not None:
                    raise ValueError('duplicate vat')
                vat = _parse_amount(stripped[len('vat:'):])
        amounts[did] = {'total': total, 'vat': vat if vat is not None else '0.00'}
    return {'name': contract['name'], 'result': {'amounts': amounts}}
