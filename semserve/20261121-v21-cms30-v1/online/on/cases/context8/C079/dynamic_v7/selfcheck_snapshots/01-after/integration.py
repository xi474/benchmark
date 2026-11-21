"""C079 integration: AES-256-GCM block encryption with verification, retry, and digest."""
from hashlib import sha256

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _sha256_hex(data: bytes) -> str:
    return sha256(data).hexdigest()


def combine(payload, left, right):
    session_key = bytes.fromhex(payload["session_key_hex"])
    base_nonce = int.from_bytes(bytes.fromhex(payload["base_nonce_hex"]), "big")
    max_retries = payload.get("max_retries", 0)
    corrupt_attempts = right  # label -> sorted unique attempt numbers within [0, max_retries]

    aesgcm = AESGCM(session_key)

    blocks = []
    attempts = []
    notifications = []
    file_hasher = sha256()
    failed_block = None
    status = "ok"

    attempt_counter = 0  # global attempt sequence number

    for kind, index, hex_data in left:
        label = f"{kind}:{index}"
        plaintext = bytes.fromhex(hex_data)
        aad = label.encode("utf-8")
        corrupt_set = set(corrupt_attempts.get(label, []))

        max_attempts = 1 + max_retries
        published = False
        first_failure_notified = False

        for attempt in range(max_attempts):
            nonce_int = base_nonce + attempt_counter
            nonce = nonce_int.to_bytes(12, "big")
            attempt_counter += 1

            ciphertext = aesgcm.encrypt(nonce, plaintext, aad)

            # Simulate transmission bit error on the last byte's lowest bit.
            if attempt in corrupt_set:
                last = ciphertext[-1]
                ciphertext = ciphertext[:-1] + bytes([last ^ 0x01])

            # Verify by decrypting and comparing with the original plaintext.
            verified = False
            try:
                decrypted = aesgcm.decrypt(nonce, ciphertext, aad)
                verified = decrypted == plaintext
            except Exception:
                verified = False

            attempts.append({"block": label, "attempt": attempt, "verified": verified})

            if verified:
                blocks.append({
                    "kind": kind,
                    "index": index,
                    "nonce_hex": nonce.hex(),
                    "ciphertext_hex": ciphertext.hex(),
                    "plaintext_sha256": _sha256_hex(plaintext),
                })
                if kind == "file":
                    file_hasher.update(plaintext)
                published = True
                break
            else:
                if not first_failure_notified:
                    notifications.append({"block": label, "error": "verification_failed"})
                    first_failure_notified = True

        if not published:
            failed_block = label
            status = "verification_failed"
            break

    return {
        "status": status,
        "failed_block": failed_block,
        "blocks": blocks,
        "attempts": attempts,
        "notifications": notifications,
        "file_sha256": file_hasher.hexdigest(),
    }
