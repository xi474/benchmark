"""C079 AES-256-GCM block encryption with verification, retry, and digest commit."""

import hashlib
import json

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _int_to_nonce(value):
    return value.to_bytes(12, "big")


def _encrypt(key, nonce, aad, plaintext):
    aesgcm = AESGCM(key)
    return aesgcm.encrypt(nonce, plaintext, aad)


def _decrypt(key, nonce, aad, ciphertext):
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, aad)


def transform(payload):
    key = bytes.fromhex(payload["session_key_hex"])
    base_nonce = int(payload["base_nonce_hex"], 16)
    file_bytes = bytes.fromhex(payload["file_hex"])
    chunk_size = payload["chunk_size"]
    max_retries = payload["max_retries"]
    thumbnail_hex = payload.get("thumbnail_hex")
    corrupt_attempts = payload.get("corrupt_attempts") or {}
    environment = payload.get("environment")

    blocks = []
    attempts = []
    notifications = []
    failed_block = None

    # Build the ordered list of (label, kind, index, plaintext) work items.
    items = []
    if thumbnail_hex is not None:
        items.append(("thumbnail:0", "thumbnail", 0, bytes.fromhex(thumbnail_hex)))
    if file_bytes or thumbnail_hex is not None:
        for i in range(0, len(file_bytes), chunk_size):
            items.append(("file:%d" % (i // chunk_size), "file", i // chunk_size,
                          file_bytes[i:i + chunk_size]))

    global_attempt = 0
    file_hasher = hashlib.sha256()

    for label, kind, index, plaintext in items:
        corrupt_set = set(corrupt_attempts.get(label, []))
        max_attempts = 1 + max_retries
        published = False
        for attempt in range(max_attempts):
            nonce = _int_to_nonce(base_nonce + global_attempt)
            global_attempt += 1
            aad = label.encode("utf-8")
            ciphertext = _encrypt(key, nonce, aad, plaintext)

            # Simulate transmission bit error by flipping the low bit of the
            # last byte of the encrypted result.
            if attempt in corrupt_set:
                corrupted = bytearray(ciphertext)
                corrupted[-1] ^= 0x01
                ciphertext = bytes(corrupted)

            verified = False
            try:
                decrypted = _decrypt(key, nonce, aad, ciphertext)
                verified = decrypted == plaintext
            except Exception:
                verified = False

            attempts.append({
                "block": label,
                "attempt": attempt,
                "verified": verified,
            })

            if verified:
                if kind == "file":
                    file_hasher.update(plaintext)
                blocks.append({
                    "kind": kind,
                    "index": index,
                    "nonce_hex": nonce.hex(),
                    "ciphertext_hex": ciphertext.hex(),
                    "plaintext_sha256": hashlib.sha256(plaintext).hexdigest(),
                })
                published = True
                break
            else:
                if attempt == 0:
                    notifications.append({
                        "block": label,
                        "error": "verification_failed",
                    })

        if not published:
            failed_block = label
            break

    file_sha256 = file_hasher.hexdigest()

    if failed_block is not None:
        status = "verification_failed"
    else:
        status = "ok"

    return {
        "status": status,
        "failed_block": failed_block,
        "blocks": blocks,
        "attempts": attempts,
        "notifications": notifications,
        "file_sha256": file_sha256,
    }


def load_payload(input_path):
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_component(input_path, output_path):
    payload = load_payload(input_path)
    result = transform(payload)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return result
