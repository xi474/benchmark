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
    classes = {}
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
        words = set(text.lower().split())
        if 'invoice' in words:
            cls = 'invoice'
        elif 'receipt' in words:
            cls = 'receipt'
        else:
            cls = 'other'
        classes[did] = cls
    return {'name': contract['name'], 'result': {'classes': classes}}
