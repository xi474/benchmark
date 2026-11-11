import math
from pathlib import Path
import numpy as np
from runtime import execute,read
root=Path(__file__).resolve().parent
report=execute(root);p=np.load(root/'outputs/dist.npy',allow_pickle=False);request=read(root/'inputs/request.json');n=request['n']
assert p.ndim==1 and p.size==n and np.isfinite(p).all() and p.min()>0 and abs(math.fsum(p)-1)<=1e-5
assert abs(math.fsum(float(x)*math.log(float(x)*n) for x in p)-request['targets']['forward'])<=.001
assert abs(math.fsum(math.log(1/(float(x)*n)) for x in p)/n-request['targets']['backward'])<=.001
assert report['result']['meets_target']
print('PUBLIC PASS')
