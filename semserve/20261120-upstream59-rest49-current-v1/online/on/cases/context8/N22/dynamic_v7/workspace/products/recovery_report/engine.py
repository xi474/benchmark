"""Implement the business transform. I/O helpers are supplied and editable here."""
from pathlib import Path
import json
import base64
import io
import tarfile
import zlib
import hashlib
import subprocess
import tempfile
import os
from runtime import build


def _extract_bundle(bundle_b64, dest):
    """Decode base64 gzip-tar bundle into dest directory."""
    data = base64.b64decode(bundle_b64)
    tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
    tf.extractall(dest)
    tf.close()


def _enumerate_objects(repo_dir):
    """Enumerate all git objects in the repo, returning list of (obj_type, content_bytes)."""
    objects = []
    obj_dir = Path(repo_dir) / ".git" / "objects"
    if not obj_dir.exists():
        return objects
    for p in obj_dir.rglob("*"):
        if not p.is_file():
            continue
        # loose objects are at .git/objects/xx/yyyy...
        rel = p.relative_to(obj_dir)
        parts = rel.parts
        if len(parts) == 2 and len(parts[0]) == 2:
            try:
                data = zlib.decompress(p.read_bytes())
            except Exception:
                continue
            objects.append(data)
        elif p.name.endswith(".pack") and p.parent.name == "pack":
            # packed objects
            objects.extend(_enumerate_pack(p))
    return objects


def _enumerate_pack(pack_path):
    """Enumerate objects from a pack file."""
    import struct
    data = pack_path.read_bytes()
    if data[:4] != b"PACK":
        return []
    version, count = struct.unpack(">II", data[4:12])
    idx = 12
    results = []
    for _ in range(count):
        # read object header (variable length)
        c = data[idx]
        idx += 1
        obj_type = (c >> 4) & 0x7
        size = c & 0x0F
        shift = 4
        while c & 0x80:
            c = data[idx]
            idx += 1
            size |= (c & 0x7F) << shift
            shift += 7
        # skip delta base if present
        if obj_type in (6, 7):  # OFS_DELTA, REF_DELTA
            if obj_type == 6:
                # ofs delta: variable length offset
                c = data[idx]
                idx += 1
                while c & 0x80:
                    c = data[idx]
                    idx += 1
            else:
                idx += 20
        # zlib stream
        d = zlib.decompressobj()
        out = d.decompress(data[idx:])
        idx += len(data[idx:]) - len(d.unused_data)
        results.append(out)
    return results


def _secret_in_content(content, secret):
    """Check if secret marker appears in object content."""
    return secret.encode("utf-8") in content


def transform(payload, contract):
    scan = payload.get("scan", {})
    cleaned = payload.get("cleaned", {})

    secret = scan.get("secret", "")
    files = cleaned.get("files", {})
    messages = cleaned.get("messages", [])
    bundle_b64 = cleaned.get("bundle", "")

    remaining = 0
    if bundle_b64:
        with tempfile.TemporaryDirectory(prefix="recovery-report-") as td:
            _extract_bundle(bundle_b64, td)
            for content in _enumerate_objects(td):
                if _secret_in_content(content, secret):
                    remaining += 1

    return {
        "secret": secret,
        "files": files,
        "messages": messages,
        "remaining_secret_objects": remaining,
    }


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(root, contract):
    return build(root, contract, transform)
