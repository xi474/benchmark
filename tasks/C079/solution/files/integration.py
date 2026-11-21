"""Author-only actual AES-GCM round-trip verification and digest reference."""
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def combine(payload, left, right):
    key=bytes.fromhex(payload['session_key_hex']);aes=AESGCM(key)
    nonce_base=int(payload['base_nonce_hex'],16)
    work=[(kind,i,bytes.fromhex(data)) for kind,i,data in left]
    blocks=[];attempts=[];notifications=[];digest=hashlib.sha256();serial=0
    for kind,index,plain in work:
        label=kind+':'+str(index);faults=right.get(label,[])
        success=False
        for attempt in range(payload['max_retries']+1):
            nonce=(nonce_base+serial).to_bytes(12,'big');serial+=1
            cipher=aes.encrypt(nonce,plain,label.encode())
            wire=cipher
            if attempt in faults:
                wire=cipher[:-1]+bytes([cipher[-1]^1])
            try:
                success=aes.decrypt(nonce,wire,label.encode())==plain
            except Exception:
                success=False
            attempts.append(dict(block=label,attempt=attempt,verified=success))
            if success:
                blocks.append(dict(kind=kind,index=index,nonce_hex=nonce.hex(),ciphertext_hex=wire.hex(),
                                   plaintext_sha256=hashlib.sha256(plain).hexdigest()))
                if kind=='file':digest.update(plain)
                break
            if attempt==0:notifications.append(dict(block=label,error='verification_failed'))
        if not success:
            return dict(status='verification_failed',failed_block=label,blocks=blocks,attempts=attempts,
                        notifications=notifications,file_sha256=digest.hexdigest())
    return dict(status='ok',failed_block=None,blocks=blocks,attempts=attempts,
                notifications=notifications,file_sha256=digest.hexdigest())

from pathlib import Path
import json
