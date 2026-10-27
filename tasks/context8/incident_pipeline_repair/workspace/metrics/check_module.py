import math
from metrics.values import finite_values
from metrics.stats import summarize
from metrics.parser import parse
def main():
 assert finite_values({'value':'4'})==[4.0]; assert finite_values({'samples':[2,'4',float('nan'),float('inf'),6]})==[2.0,4.0,6.0]
 assert summarize([2,4,6])=={'min':2.0,'max':6.0,'mean':4.0}; assert parse({'source':'x','samples':[2,'4',float('nan'),6]})=={'source':'x','min':2.0,'max':6.0,'mean':4.0}
