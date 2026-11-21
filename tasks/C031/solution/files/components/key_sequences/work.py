KEYS={'Enter':b'\r','C-c':b'\x03','C-d':b'\x04','C-u':b'\x15','Tab':b'\t','Backspace':b'\x7f'}


def compute(p):
 return [b''.join(KEYS[k] if k in KEYS else k.encode() for k in s['keys']).hex() for s in p['steps']]
