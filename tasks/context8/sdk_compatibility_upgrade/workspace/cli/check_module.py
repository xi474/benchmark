from cli.names import canonical_name
from cli.values import canonical_value
from cli.adapter import adapt_args
def main():
 assert canonical_name('--timeout')=='request_timeout' and canonical_name('--request-timeout')=='request_timeout'; assert canonical_value('retries','3')==3 and canonical_value('verify',True) is False
 src={'--timeout':'30','--retries':'3','--no-verify':True}; assert adapt_args(src)=={'request_timeout':30,'retries':3,'verify':False}
 try: adapt_args({'--timeout':'10','--request-timeout':'20'})
 except ValueError: pass
 else: raise AssertionError('conflict')
