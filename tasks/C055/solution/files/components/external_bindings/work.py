def compute(p):
    values={}
    for index,src in enumerate(p['sources']):
        if src['trusted']!=False:continue
        anchors={}
        for i,line in enumerate(src['yaml'].splitlines(),1):
            if line=='---':
                anchors={}
                continue
            if not line:continue
            key,body=line.split(': ',1)
            pos=[src['name'],i,len(key)+3]
            if body.startswith('*'):
                value=anchors[body[1:]]
            else:
                anchor=None
                if body.startswith('&'):
                    anchor,body=body[1:].split(' ',1)
                vault=body.startswith('!vault ')
                data=body[7:] if vault else body
                value=(pos,data,vault,src['trusted'])
                if anchor:anchors[anchor]=value
            values[key]=(index,[src['name'],i,1],value)
    return values
