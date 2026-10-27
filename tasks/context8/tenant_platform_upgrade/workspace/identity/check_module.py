from identity.normalize import norm,normalize_request
from identity.policy import decide
from identity.service import authorize
def main():
 assert norm(' Editor ')=='editor'; src={'tenant':' ACME ','user':' U1 ','role':' Editor '}; got=normalize_request(src); assert got=={'tenant':'acme','user':'u1','role':'editor'} and src['tenant']==' ACME '
 p={'tenant':'acme','minimum_role':'editor','denied_users':['blocked']}; assert decide(got,p,{'owner':3,'editor':2,'viewer':1})==(True,'authorized')
 assert decide({'tenant':'other','user':'u1','role':'owner'},p,{'owner':3})==(False,'tenant_mismatch')
 assert authorize(src,p)=={'allowed':True,'role':'editor','reason':'authorized'}
