import json
import math


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)



def _reject_nonfinite(obj):
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError('non-finite number')
    elif isinstance(obj, dict):
        for v in obj.values():
            _reject_nonfinite(v)
    elif isinstance(obj, list):
        for v in obj:
            _reject_nonfinite(v)

def transform(payloads, contract):
    _reject_nonfinite(payloads)
    _reject_nonfinite(contract)
    if not isinstance(contract, dict) or 'name' not in contract:
        raise ValueError('bad contract')
    if not isinstance(payloads, list) or len(payloads) != len(contract.get('inputs', [])):
        raise ValueError('payload count mismatch')
    if contract.get('operation') != 'reshard_layout':
        raise ValueError('wrong operation')

    original = payloads[0]
    chunks_result = payloads[1]
    if not isinstance(original, dict):
        raise ValueError('original input must be object')
    if not isinstance(chunks_result, dict) or 'result' not in chunks_result:
        raise ValueError('chunks input must be wrapped result')

    max_file_bytes = original.get('max_file_bytes')
    max_entries = original.get('max_entries')
    if not _is_int(max_file_bytes) or max_file_bytes < 16:
        raise ValueError('max_file_bytes invalid')
    if not _is_int(max_entries) or max_entries < 2:
        raise ValueError('max_entries invalid')

    cr = chunks_result['result']
    if not isinstance(cr, dict) or 'chunks' not in cr or 'manifest' not in cr:
        raise ValueError('bad chunks result')
    chunks = cr['chunks']
    manifest = cr['manifest']
    if not isinstance(chunks, list) or not isinstance(manifest, dict) or 'files' not in manifest:
        raise ValueError('bad chunks structure')

    # Build manifest compact JSON bytes
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

    # Metadata chunks
    meta_chunks = []
    counter = 0
    for i in range(0, len(manifest_bytes), max_file_bytes):
        piece = manifest_bytes[i:i + max_file_bytes]
        name = 'm%06d.bin' % counter
        counter += 1
        meta_chunks.append({'name': name, 'hex': piece.hex()})

    # Combine data chunks and metadata chunks, sort by name
    all_items = []
    for c in chunks:
        if not isinstance(c, dict) or 'name' not in c or 'hex' not in c:
            raise ValueError('bad chunk')
        all_items.append({'name': c['name'], 'hex': c['hex']})
    all_items.extend(meta_chunks)
    all_items.sort(key=lambda x: x['name'])

    N = len(all_items)
    # find minimal h >= 1 such that max_entries**h >= N
    h = 1
    while max_entries ** h < N:
        h += 1

    tree = []
    for i, item in enumerate(all_items):
        # convert i to exactly h digits base max_entries
        digits = []
        x = i
        for _ in range(h):
            digits.append(x % max_entries)
            x //= max_entries
        digits.reverse()
        # first h-1 digits become directory levels n<digit>
        dirs = ['n%d' % d for d in digits[:-1]]
        path = '/'.join(dirs + [item['name']]) if dirs else item['name']
        tree.append({'path': path, 'hex': item['hex']})

    tree.sort(key=lambda x: x['path'])

    result = {
        'tree': tree,
        'max_entries': max_entries,
        'max_file_bytes': max_file_bytes,
    }
    return {'name': contract['name'], 'result': result}
