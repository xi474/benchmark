from metrics.check_module import main as check_metrics
from traces.check_module import main as check_traces
from logs.check_module import main as check_logs
import json, math
from metrics.parser import parse as pm
from traces.parser import parse as pt
from logs.parser import parse as pl
from incident import combine

def main():
    check_metrics(); check_traces(); check_logs()
    assert pm({'source':'old','value':4})=={'source':'old','min':4.0,'max':4.0,'mean':4.0}
    assert pm({'source':'new','samples':[2,'4',float('nan'),6]})=={'source':'new','min':2.0,'max':6.0,'mean':4.0}
    nested={'id':'r','service':'api','duration':2,'error':False,'children':[{'id':'d','service':'db','duration':5,'error':True,'children':[]},{'id':'q','service':'queue','duration':3,'error':False,'children':[{'id':'w','service':'worker','duration':4,'error':True,'children':[]}]}]}
    assert pt(nested)=={'error_services':['db','worker'],'critical_path':9.0}
    flat=[{'id':'r','parent':None,'service':'api','duration':2,'error':False},{'id':'d','parent':'r','service':'db','duration':5,'error':True}]
    assert pt(flat)=={'error_services':['db'],'critical_path':7.0}
    got=pl(['INFO ready','ERROR token=abc',json.dumps({'level':'warn','message':'password=hunter2 secret = zz'})])
    assert got['counts']=={'error':1,'info':1,'warn':1}
    joined=' '.join(got['lines']).lower(); assert 'abc' not in joined and 'hunter2' not in joined and 'zz' not in joined and '[redacted]' in joined
    assert combine(pm({'source':'x','value':1}),pt(flat),got)['has_error'] is True
    print('PASS incident_pipeline_repair')
if __name__=='__main__': main()
