import hashlib
import json
import re


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


_NAME_RE = re.compile(r'^[md][0-9]{6}\.bin$')


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
    if contract.get('operation') != 'reshard_restore':
        raise ValueError('wrong operation')

    layout = payloads[0]
    if not isinstance(layout, dict) or 'result' not in layout:
        raise ValueError('layout input must be wrapped result')
    lr = layout['result']
    if not isinstance(lr, dict) or 'tree' not in lr or 'max_entries' not in lr or 'max_file_bytes' not in lr:
        raise ValueError('bad layout result')
    tree = lr['tree']
    max_entries = lr['max_entries']
    max_file_bytes = lr['max_file_bytes']
    if not isinstance(tree, list):
        raise ValueError('tree must be list')
    if not _is_int(max_entries) or max_entries < 2:
        raise ValueError('max_entries invalid')
    if not _is_int(max_file_bytes) or max_file_bytes < 16:
        raise ValueError('max_file_bytes invalid')

    # Validate tree structure
    entries = []
    basenames = set()
    for item in tree:
        if not isinstance(item, dict) or 'path' not in item or 'hex' not in item:
            raise ValueError('bad tree entry')
        path = _safe_path(item['path'])
        hx = item['hex']
        if not isinstance(hx, str):
            raise ValueError('hex must be string')
        try:
            raw = bytes.fromhex(hx)
        except ValueError:
            raise ValueError('bad hex')
        if len(raw) > max_file_bytes:
            raise ValueError('file exceeds max_file_bytes')
        base = path.split('/')[-1]
        if not _NAME_RE.match(base):
            raise ValueError('bad basename')
        if base in basenames:
            raise ValueError('duplicate basename')
        basenames.add(base)
        entries.append((path, base, raw))

    # Check per-directory entry count (files + subdirs)
    dir_counts = {}
    for path, base, raw in entries:
        parts = path.split('/')
        # each directory prefix
        for depth in range(1, len(parts)):
            d = '/'.join(parts[:depth])
            dir_counts.setdefault(d, set()).add(parts[depth])
    for d, children in dir_counts.items():
        if len(children) > max_entries:
            raise ValueError('directory exceeds max_entries')

    # Separate m and d blocks
    m_blocks = {}
    d_blocks = {}
    for path, base, raw in entries:
        num = int(base[1:7])
        if base[0] == 'm':
            if num in m_blocks:
                raise ValueError('duplicate m block')
            m_blocks[num] = raw
        else:
            if num in d_blocks:
                raise ValueError('duplicate d block')
            d_blocks[num] = raw

    # m blocks must be contiguous from 0
    m_nums = sorted(m_blocks.keys())
    if m_nums != list(range(len(m_nums))):
        raise ValueError('m blocks not contiguous')

    manifest_bytes = b''.join(m_blocks[i] for i in m_nums)
    try:
        manifest = json.loads(manifest_bytes.decode('utf-8'))
    except Exception:
        raise ValueError('bad manifest JSON')
    if not isinstance(manifest, dict) or 'files' not in manifest:
        raise ValueError('bad manifest')
    files = manifest['files']
    if not isinstance(files, list):
        raise ValueError('manifest files must be list')

    # Reconstruct files
    used_d = set()
    result_files = []
    total_bytes = 0
    seen_paths = set()
    for f in files:
        if not isinstance(f, dict) or 'path' not in f or 'size' not in f or 'sha256' not in f or 'parts' not in f:
            raise ValueError('bad manifest file')
        path = _safe_path(f['path'])
        if path in seen_paths:
            raise ValueError('duplicate manifest path')
        seen_paths.add(path)
        size = f['size']
        if not _is_int(size) or size < 0:
            raise ValueError('bad size')
        sha = f['sha256']
        if not isinstance(sha, str):
            raise ValueError('bad sha256')
        parts = f['parts']
        if not isinstance(parts, list):
            raise ValueError('parts must be list')
        data = b''
        for p in parts:
            if not isinstance(p, str) or not _NAME_RE.match(p) or p[0] != 'd':
                raise ValueError('bad part name')
            num = int(p[1:7])
            if num in used_d:
                raise ValueError('d block referenced twice')
            used_d.add(num)
            if num not in d_blocks:
                raise ValueError('missing d block')
            data += d_blocks[num]
        if len(data) != size:
            raise ValueError('size mismatch')
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError('sha256 mismatch')
        result_files.append({'path': path, 'hex': data.hex()})
        total_bytes += size

    # every d block must be referenced exactly once
    if set(d_blocks.keys()) != used_d:
        raise ValueError('extra or unreferenced d block')

    result_files.sort(key=lambda x: x['path'])

    result = {
        'files': result_files,
        'total_bytes': total_bytes,
    }
    return {'name': contract['name'], 'result': result}
