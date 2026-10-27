from config.coerce import coerce_like
from config.merge import deep_merge
from config.loader import load_config
def main():
 assert coerce_like('true',False) is True and coerce_like('5',2)==5 and coerce_like('3.5',1.0)==3.5
 a={'x':1,'http':{'timeout':10,'verify':True}}; b=deep_merge(a,{'http':{'timeout':20}}); assert b=={'x':1,'http':{'timeout':20,'verify':True}} and a['http']['timeout']==10
 got=load_config({'retries':2,'debug':False,'http':{'timeout':10,'verify':True}},{'http':{'timeout':20}},{'SDK_DEBUG':'true','SDK_HTTP__VERIFY':'false'},{'retries':'5'}); assert got=={'retries':5,'debug':True,'http':{'timeout':20,'verify':False}}
