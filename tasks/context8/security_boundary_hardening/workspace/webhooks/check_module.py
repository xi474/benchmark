import hashlib,hmac
from webhooks.signature import expected,matches
from webhooks.replay import consume
from webhooks.verify import verify
def main():
 body=b'{}'; sig=hmac.new(b'key',b'1000.'+body,hashlib.sha256).hexdigest(); assert expected(1000,body,'key')==sig and matches(sig,sig) and not matches(sig,'00')
 seen=set(); assert consume('x',seen) and not consume('x',seen)
 seen=set(); assert verify(1000,body,sig,'key',1100,seen)==(True,'ok') and verify(1000,body,sig,'key',1100,seen)==(False,'replay')
