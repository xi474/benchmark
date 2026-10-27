from sessions.codec import encode,decode
from sessions.claims import validate
from sessions.tokens import issue,verify
def main():
 raw={'sub':'alice','exp':200}; assert decode(encode(raw))==raw; assert validate(raw,100)=='alice' and validate(raw,201) is None and validate({'exp':2},1) is None
 t=issue('alice',200,'sekret'); assert t.count('.')==2 and verify(t,100,'sekret')=='alice' and verify(t,201,'sekret') is None and verify(t+'x',100,'sekret') is None
