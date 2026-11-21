import numpy as np
def compute(payload):
    layers=[(np.asarray(x['weight'],dtype=np.float64),np.asarray(x['bias'],dtype=np.float64)) for x in payload['layers']]
    world=payload['world_size'];n=len(layers);micro=payload['microbatches'];m=len(micro)
    cuts=[n*r//world for r in range(world+1)]
    slots={};events=[];loss=0.;dweights=[np.zeros_like(w) for w,b in layers];dbias=[np.zeros_like(b) for w,b in layers]
    out_grad={}
    for bi,batch in enumerate(micro):
        x=np.asarray(batch['inputs'],dtype=np.float64)
        for stage in range(world):
            pass
            for li in range(cuts[stage],cuts[stage+1]):
                w,b=layers[li];z=x@w.T+b
                y=z if li==n-1 else np.tanh(z)
                slots[bi,li]=(x,y)
                x=y
            if stage<world-1:
                pass
        labels=np.asarray(batch['targets'],dtype=int)
        shifted=x-x.max(axis=1,keepdims=True);exp=np.exp(shifted);probs=exp/exp.sum(axis=1,keepdims=True)
        loss+=float((-shifted[np.arange(len(labels)),labels]+np.log(exp.sum(axis=1))).mean())/m
        g=probs.copy();g[np.arange(len(labels)),labels]-=1.;g/=len(labels)*m
        out_grad[bi]=g
    for bi in reversed(range(m)):
        g=out_grad[bi]
        for stage in reversed(range(world)):
            pass
            for li in reversed(range(cuts[stage],cuts[stage+1])):
                x,y=slots[bi,li];w,b=layers[li]
                dz=g if li==n-1 else g*(1-y*y)
                dweights[li]+=dz.T@x;dbias[li]+=dz.sum(axis=0)
                g=dz@w
            if stage>0:
                pass
    clean=lambda a:np.round(a,12).tolist()
    return dict(loss=round(loss,12),gradients=[dict(weight=clean(w),bias=clean(b)) for w,b in zip(dweights,dbias)])
