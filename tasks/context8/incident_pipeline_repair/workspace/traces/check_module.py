from traces.graph import roots_and_children
from traces.analysis import analyze
from traces.parser import parse
N={'id':'r','service':'api','duration':2,'error':False,'children':[{'id':'d','service':'db','duration':5,'error':True,'children':[]},{'id':'q','service':'queue','duration':3,'error':False,'children':[{'id':'w','service':'worker','duration':4,'error':True,'children':[]}]}]}
def main():
 roots,kids=roots_and_children(N); assert roots==['r'] and sorted(kids)==['d','q','r','w']; assert analyze(roots,kids)==(['db','worker'],9.0); assert parse(N)=={'error_services':['db','worker'],'critical_path':9.0}
