"""Implement the business transform. I/O helpers are supplied and editable here."""
from pathlib import Path
import json
import base64
import io
import tarfile
import zlib
import re
from runtime import build


def _extract_bundle(bundle_b64):
    data = base64.b64decode(bundle_b64)
    tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
    return tf


def _iter_objects(tf):
    for member in tf.getmembers():
        if not member.isfile():
            continue
        parts = member.name.split("/")
        # .git/objects/xx/yyyy...
        if len(parts) >= 4 and parts[0] == ".git" and parts[1] == "objects":
            yield member


def transform(payload, contract):
    bundle_b64 = payload["bundle"]
    tf = _extract_bundle(bundle_b64)
    secret = None
    for member in _iter_objects(tf):
        raw = tf.extractfile(member).read()
        try:
            data = zlib.decompress(raw)
        except zlib.error:
            continue
        # data begins with "<type> <size>\0<content>"
        m = re.search(rb"secret\[[^\]]*\]", data)
        if m:
            secret = m.group(0).decode("utf-8")
            break
    if secret is None:
        raise ValueError("secret marker not found in git objects")
    return {"secret": secret}


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(root, contract):
    return build(root, contract, transform)
