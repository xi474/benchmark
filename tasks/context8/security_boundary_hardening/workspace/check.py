from sessions.check_module import main as check_sessions
from webhooks.check_module import main as check_webhooks
from exports.check_module import main as check_exports
import base64, hashlib, hmac, json, tempfile, time
from pathlib import Path
from sessions.tokens import issue, verify as verify_token
from webhooks.verify import verify as verify_hook
from exports.paths import resolve_export

def main():
    check_sessions(); check_webhooks(); check_exports()
    token=issue('alice',200,'sekret'); assert token.count('.')==2
    assert verify_token(token,100,'sekret')=='alice'; assert verify_token(token,201,'sekret') is None
    assert verify_token(token+'x',100,'sekret') is None and verify_token('bad',100,'sekret') is None
    body=b'{"ok":true}'; ts=1000; sig=hmac.new(b'key',str(ts).encode()+b'.'+body,hashlib.sha256).hexdigest(); seen=set()
    assert verify_hook(ts,body,sig,'key',1100,seen)==(True,'ok')
    assert verify_hook(ts,body,sig,'key',1100,seen)==(False,'replay')
    assert verify_hook(ts,body,'00','key',1100,set())==(False,'signature')
    assert verify_hook(ts,body,sig,'key',1401,set())==(False,'timestamp')
    with tempfile.TemporaryDirectory() as td:
        base=Path(td); good=resolve_export(base,'acme','reports/a.json'); assert good==base/'acme'/'reports'/'a.json' and (base/'acme').is_dir()
        for bad in ('../escape','/absolute','reports/../../escape'):
            try: resolve_export(base,'acme',bad)
            except ValueError: pass
            else: raise AssertionError(bad)
        outside=base/'outside'; outside.mkdir(); link=base/'acme'/'link'
        try:
            link.symlink_to(outside,target_is_directory=True)
            try: resolve_export(base,'acme','link/x.json')
            except ValueError: pass
            else: raise AssertionError('symlink escape')
        except OSError: pass
    print('PASS security_boundary_hardening')
if __name__=='__main__': main()
