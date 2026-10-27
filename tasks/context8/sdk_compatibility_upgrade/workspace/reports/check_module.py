import json
from reports.upgrade import upgrade_record
from reports.canonical import dump_bytes
from reports.serializer import serialize_report
def main():
 assert upgrade_record({'name':'b','ok':True,'elapsed':1.2,'tag':'x'})=={'id':'b','status':'passed','duration_ms':1200,'extensions':{'tag':'x'}}
 assert dump_bytes({'b':1,'a':2})==b'{"a":2,"b":1}'
 raw=serialize_report([{'name':'b','ok':True,'elapsed':1.2,'tag':'x'},{'id':'a','status':'failed','duration_ms':7,'extra':9}],{'build':'z','version':99}); assert json.loads(raw)=={'version':2,'extensions':{'build':'z','version':99},'records':[{'id':'a','status':'failed','duration_ms':7,'extensions':{'extra':9}},{'id':'b','status':'passed','duration_ms':1200,'extensions':{'tag':'x'}}]}
