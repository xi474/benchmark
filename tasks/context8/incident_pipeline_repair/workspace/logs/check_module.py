import json
from logs.levels import split_line
from logs.redact import redact
from logs.parser import parse
def main():
 assert split_line('ERROR token=abc')==('error','token=abc'); assert split_line(json.dumps({'level':'warn','message':'password=hunter2'}))==('warn','password=hunter2')
 assert redact('token=abc password = xyz secret:q')=='token=[redacted] password = [redacted] secret:[redacted]'
 got=parse(['INFO ready','ERROR token=abc',json.dumps({'level':'warn','message':'password=hunter2 secret = zz'})]); assert got['counts']=={'error':1,'info':1,'warn':1}; assert not any(x in ' '.join(got['lines']) for x in ['abc','hunter2','zz'])
