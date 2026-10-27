from config.check_module import main as check_config
from cli.check_module import main as check_cli
from reports.check_module import main as check_reports
import json
from config.loader import load_config
from cli.adapter import adapt_args
from reports.serializer import serialize_report

def main():
    check_config(); check_cli(); check_reports()
    defaults={'retries':2,'debug':False,'http':{'timeout':10,'verify':True}}
    got=load_config(defaults,{'http':{'timeout':20}}, {'SDK_DEBUG':'true','SDK_HTTP__VERIFY':'false'}, {'retries':'5'})
    assert got=={'retries':5,'debug':True,'http':{'timeout':20,'verify':False}},got
    assert defaults['http']['timeout']==10
    source={'--timeout':'30','--retries':'3','--no-verify':True}; frozen=dict(source)
    assert adapt_args(source)=={'request_timeout':30,'retries':3,'verify':False}; assert source==frozen
    try: adapt_args({'--timeout':'10','--request-timeout':'20'})
    except ValueError: pass
    else: raise AssertionError('alias conflict')
    rows=[{'name':'b','ok':True,'elapsed':1.2,'tag':'x'},{'id':'a','status':'failed','duration_ms':7,'extra':9}]
    raw=serialize_report(rows,{'build':'z','version':99}); assert isinstance(raw,bytes)
    assert raw==b'{"extensions":{"build":"z","version":99},"records":[{"duration_ms":7,"extensions":{"extra":9},"id":"a","status":"failed"},{"duration_ms":1200,"extensions":{"tag":"x"},"id":"b","status":"passed"}],"version":2}',raw
    print('PASS sdk_compatibility_upgrade')
if __name__=='__main__': main()
