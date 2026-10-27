from identity.check_module import main as check_identity
from billing.check_module import main as check_billing
from notify.check_module import main as check_notify
import hashlib, html, json
from decimal import Decimal
from identity.service import authorize
from billing.service import invoice
from notify.service import build_delivery

def main():
    check_identity(); check_billing(); check_notify()
    p={'tenant':'acme','minimum_role':'editor','denied_users':['blocked']}
    assert authorize({'tenant':'acme','user':'u1','role':' Editor '},p)=={'allowed':True,'role':'editor','reason':'authorized'}
    assert authorize({'tenant':'other','user':'u1','role':'owner'},p)['reason']=='tenant_mismatch'
    assert authorize({'tenant':'acme','user':'blocked','role':'owner'},p)['reason']=='role_denied'
    pricing={'acme':{'cpu':'0.125','io':'0.055','credit':'0.10'}}
    events=[{'id':'b','tenant':'acme','kind':'cpu','units':3},{'id':'a','tenant':'acme','kind':'io','units':2},{'id':'b','tenant':'acme','kind':'cpu','units':3}]
    got=invoice(events,pricing)
    assert got['currency']=='USD' and got['total']=='0.39',got
    assert [x['event_id'] for x in got['lines']]==['a','b'] and all(isinstance(x['amount'],str) for x in got['lines'])
    msg={'tenant':'acme','recipient':'r1','id':'m7','body':'<b>Hello & bye</b>'}
    d=build_delivery(msg,{'email':False,'sms':True,'push':True})
    assert d['channel']=='sms' and d['body']==html.escape(msg['body'])
    expected=hashlib.sha256(b'acme|r1|m7|sms').hexdigest()
    assert d['idempotency_key']==expected
    print('PASS tenant_platform_upgrade')
if __name__=='__main__': main()
