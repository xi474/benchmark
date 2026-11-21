"""Implement the business transform. I/O helpers are supplied and editable here."""
from pathlib import Path
import json
import base64
import hashlib
import io
import os
import shutil
import tarfile
import tempfile
import zlib

from runtime import build


def _decode_bundle(bundle_b64):
    raw = base64.b64decode(bundle_b64)
    return tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz")


def _extract_bundle(bundle_b64, dest):
    tf = _decode_bundle(bundle_b64)
    tf.extractall(dest)
    tf.close()


def _read_object(repo, sha):
    """Return (type, payload_bytes) for a git object, or None."""
    obj_path = os.path.join(repo, ".git", "objects", sha[:2], sha[2:])
    if not os.path.isfile(obj_path):
        return None
    with open(obj_path, "rb") as fh:
        data = zlib.decompress(fh.read())
    header, _, body = data.partition(b"\x00")
    otype = header.split(b" ")[0].decode("utf-8")
    return otype, body


def _iter_objects(repo):
    """Yield (sha, type) for every loose object in the repo."""
    base = os.path.join(repo, ".git", "objects")
    for d in os.listdir(base):
        dd = os.path.join(base, d)
        if not os.path.isdir(dd) or len(d) != 2:
            continue
        for f in os.listdir(dd):
            sha = d + f
            obj = _read_object(repo, sha)
            if obj is not None:
                yield sha, obj[0]


def _parse_commit(body):
    """Return dict with tree, parents, message."""
    text = body.decode("utf-8", "replace")
    headers, _, message = text.partition("\n\n")
    tree = None
    parents = []
    for line in headers.split("\n"):
        if line.startswith("tree "):
            tree = line[5:].strip()
        elif line.startswith("parent "):
            parents.append(line[7:].strip())
    return {"tree": tree, "parents": parents, "message": message}


def _parse_tree(body):
    """Return list of (mode, name, sha) entries."""
    entries = []
    i = 0
    n = len(body)
    while i < n:
        sp = body.index(b" ", i)
        mode = body[i:sp].decode("ascii")
        i = sp + 1
        nul = body.index(b"\x00", i)
        name = body[i:nul].decode("utf-8", "replace")
        i = nul + 1
        sha = body[i:i + 20].hex()
        i += 20
        entries.append((mode, name, sha))
    return entries


def _reachable_objects(repo, head_sha):
    """Return set of reachable object shas from head commit."""
    reachable = set()
    stack = [head_sha]
    while stack:
        sha = stack.pop()
        if sha in reachable:
            continue
        obj = _read_object(repo, sha)
        if obj is None:
            continue
        otype, body = obj
        reachable.add(sha)
        if otype == "commit":
            c = _parse_commit(body)
            if c["tree"]:
                stack.append(c["tree"])
            stack.extend(c["parents"])
        elif otype == "tree":
            for mode, name, child in _parse_tree(body):
                stack.append(child)
    return reachable


def _resolve_head(repo):
    head_path = os.path.join(repo, ".git", "HEAD")
    with open(head_path, "rb") as fh:
        content = fh.read().decode("utf-8", "replace").strip()
    if content.startswith("ref: "):
        ref = content[5:].strip()
        ref_path = os.path.join(repo, ".git", ref)
        if os.path.isfile(ref_path):
            with open(ref_path, "rb") as fh:
                return fh.read().decode("utf-8", "replace").strip()
        return None
    return content


def _commit_messages(repo, head_sha):
    """Return commit messages newest-first."""
    messages = []
    seen = set()
    stack = [head_sha]
    while stack:
        sha = stack.pop(0)
        if sha in seen:
            continue
        seen.add(sha)
        obj = _read_object(repo, sha)
        if obj is None or obj[0] != "commit":
            continue
        c = _parse_commit(obj[1])
        messages.append(c["message"].strip())
        stack.extend(c["parents"])
    return messages


def _working_files(repo):
    """Return {relative_path: sha256} for non-.git files."""
    files = {}
    for root, dirs, names in os.walk(repo):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in names:
            p = os.path.join(root, name)
            rel = os.path.relpath(p, repo).replace(os.sep, "/")
            with open(p, "rb") as fh:
                files[rel] = hashlib.sha256(fh.read()).hexdigest()
    return files


def _clean_reflog(repo, reachable):
    """Remove reflog lines referencing non-reachable commits."""
    logs_dir = os.path.join(repo, ".git", "logs")
    if not os.path.isdir(logs_dir):
        return
    for root, dirs, names in os.walk(logs_dir):
        for name in names:
            p = os.path.join(root, name)
            with open(p, "rb") as fh:
                lines = fh.read().decode("utf-8", "replace").split("\n")
            kept = []
            for line in lines:
                if not line.strip():
                    continue
                parts = line.split("\t", 1)
                if not parts:
                    continue
                fields = parts[0].split(" ")
                old = fields[0] if len(fields) > 0 else ""
                new = fields[1] if len(fields) > 1 else ""
                if old in reachable and new in reachable:
                    kept.append(line)
            with open(p, "wb") as fh:
                fh.write(("\n".join(kept) + ("\n" if kept else "")).encode("utf-8"))


def _clean_orig_head(repo, reachable):
    p = os.path.join(repo, ".git", "ORIG_HEAD")
    if os.path.isfile(p):
        with open(p, "rb") as fh:
            sha = fh.read().decode("utf-8", "replace").strip()
        if sha not in reachable:
            os.remove(p)


def _delete_unreachable(repo, reachable):
    base = os.path.join(repo, ".git", "objects")
    for d in os.listdir(base):
        dd = os.path.join(base, d)
        if not os.path.isdir(dd) or len(d) != 2:
            continue
        for f in os.listdir(dd):
            sha = d + f
            if sha not in reachable:
                os.remove(os.path.join(dd, f))


def _pack_dir(src):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        tf.add(src, arcname=".")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def transform(payload, contract):
    bundle_b64 = payload["bundle"]
    scan = payload.get("scan") or {}
    secret = scan.get("secret")

    tmp = tempfile.mkdtemp(prefix="cleaned-repo-")
    try:
        _extract_bundle(bundle_b64, tmp)

        head_sha = _resolve_head(tmp)
        if not head_sha:
            raise ValueError("cannot resolve HEAD")

        reachable = _reachable_objects(tmp, head_sha)

        # Confirm the recovered secret is present in the repo before cleaning.
        if secret is not None:
            found = False
            for sha, otype in _iter_objects(tmp):
                if otype == "blob":
                    _, body = _read_object(tmp, sha)
                    if body.decode("utf-8", "replace") == secret:
                        found = True
                        break
            if not found:
                raise ValueError("secret not found in repository")

        _delete_unreachable(tmp, reachable)
        _clean_reflog(tmp, reachable)
        _clean_orig_head(tmp, reachable)

        files = _working_files(tmp)
        messages = _commit_messages(tmp, head_sha)
        bundle_out = _pack_dir(tmp)

        return {
            "bundle": bundle_out,
            "files": files,
            "messages": messages,
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(root, contract):
    return build(root, contract, transform)
