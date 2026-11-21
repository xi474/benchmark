import hashlib
import math


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _safe_path(p):
    if not isinstance(p, str):
        raise ValueError('path must be string')
    if p == '' or p != p.strip():
        raise ValueError('path must be non-empty and stripped')
    if p.startswith('/') or '\\' in p or ':' in p:
        raise ValueError('unsafe path')
    parts = p.split('/')
    if any(seg in ('', '.', '..') for seg in parts):
        raise ValueError('unsafe path segment')
    return p


def transform(payloads, contract):
    if not isinstance(contract, dict) or 'name' not in contract:
        raise ValueError('bad contract')
    if not isinstance(payloads, list) or len(payloads) != len(contract.get('inputs', [])):
        raise ValueError('payload count mismatch')
    if contract.get('operation') != 'reshard_chunks':
        raise ValueError('wrong operation')

    data = payloads[0]
    if not isinstance(data, dict):
        raise ValueError('input must be object')
    if 'files' not in data or 'max_file_bytes' not in data or 'max_entries' not in data:
        raise ValueError('missing required field')
    files = data['files']
    max_file_bytes = data['max_file_bytes']
    max_entries = data['max_entries']
    if not isinstance(files, list):
        raise ValueError('files must be list')
    if not _is_int(max_file_bytes) or max_file_bytes < 16:
        raise ValueError('max_file_bytes invalid')
    if not _is_int(max_entries) or max_entries < 2:
        raise ValueError('max_entries invalid')

    seen = set()
    parsed = []
    for f in files:
        if not isinstance(f, dict) or 'path' not in f or 'hex' not in f:
            raise ValueError('bad file entry')
        path = _safe_path(f['path'])
        if path in seen:
            raise ValueError('duplicate path')
        seen.add(path)
        hx = f['hex']
        if not isinstance(hx, str):
            raise ValueError('hex must be string')
        try:
            raw = bytes.fromhex(hx)
        except ValueError:
            raise ValueError('bad hex')
        parsed.append((path, raw))

    parsed.sort(key=lambda t: t[0])

    chunks = []
    manifest_files = []
    counter = 0
    for path, raw in parsed:
        parts = []
        for i in range(0, len(raw), max_file_bytes):
            piece = raw[i:i + max_file_bytes]
            name = 'd%06d.bin' % counter
            counter += 1
            chunks.append({'name': name, 'hex': piece.hex()})
            parts.append(name)
        manifest_files.append({
            'path': path,
            'size': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(),
            'parts': parts,
        })

    result = {
        'chunks': chunks,
        'manifest': {'files': manifest_files},
    }
    return {'name': contract['name'], 'result': result}
