"""Author-only actual AES-GCM round-trip verification and digest reference."""
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def transform(payload):
    key=bytes.fromhex(payload['session_key_hex']);aes=AESGCM(key)
    file=bytes.fromhex(payload['file_hex']);size=payload['chunk_size'];nonce_base=int(payload['base_nonce_hex'],16)
    chunks=[file[i:i+size] for i in range(0,len(file),size)]
    work=[]
    if payload.get('thumbnail_hex') is not None:
        work.append(('thumbnail',0,bytes.fromhex(payload['thumbnail_hex'])))
    work.extend(('file',i,c) for i,c in enumerate(chunks))
    blocks=[];attempts=[];notifications=[];digest=hashlib.sha256();serial=0
    for kind,index,plain in work:
        label=kind+':'+str(index);faults=payload.get('corrupt_attempts',{}).get(label,[])
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
def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def build_component(input_path,output_path):
    value=transform(load_payload(input_path))
    p=Path(output_path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return value
