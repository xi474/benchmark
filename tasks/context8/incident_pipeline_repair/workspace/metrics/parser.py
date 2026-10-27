def parse(payload):
    values = payload['samples']
    return {'source':payload['source'],'min':min(values),'max':max(values),'mean':sum(values)/len(values)}
