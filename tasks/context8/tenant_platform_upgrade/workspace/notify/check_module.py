import hashlib,html
from notify.channels import choose
from notify.render import safe_body,delivery_key
from notify.service import build_delivery
def main():
 prefs={'email':False,'sms':True,'push':True}; assert choose(prefs,['email','sms','push'])=='sms'; assert safe_body('<b>x&y</b>')==html.escape('<b>x&y</b>')
 msg={'tenant':'acme','recipient':'r1','id':'m7','body':'<b>Hello & bye</b>'}; key=hashlib.sha256(b'acme|r1|m7|sms').hexdigest(); assert delivery_key(msg,'sms')==key
 assert build_delivery(msg,prefs)=={'channel':'sms','body':html.escape(msg['body']),'idempotency_key':key}
