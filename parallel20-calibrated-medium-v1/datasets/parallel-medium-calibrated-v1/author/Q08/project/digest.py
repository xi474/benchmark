MASS={"A":71,"C":103,"D":115,"E":129,"K":128,"P":97,"R":156}

def boundaries(sequence):
    cuts=[0]
    for index,residue in enumerate(sequence):
        if residue in "KR" and (index+1==len(sequence) or sequence[index+1]!="P"):
            cuts.append(index+1)
    if cuts[-1]!=len(sequence):cuts.append(len(sequence))
    return cuts

def enumerate_candidates(proteins,modifications):
    result=[]
    for protein in proteins:
        for kind,sequence in (("target",protein["sequence"]),("decoy",protein["sequence"][::-1])):
            cuts=boundaries(sequence)
            for start_index in range(len(cuts)-1):
                for segments in (1,2):
                    end_index=start_index+segments
                    if end_index>=len(cuts):continue
                    start,end=cuts[start_index],cuts[end_index]
                    peptide=sequence[start:end]
                    if len(peptide)<2:continue
                    variants=[("none",None,0)]
                    for mod in modifications:
                        for position,residue in enumerate(peptide):
                            if residue==mod["residue"]:
                                variants.append((f'{mod["name"]}@{start+position+1}',position,mod["shift"]))
                    for tag,position,shift in variants:
                        masses=[MASS[residue]+(shift if position==index else 0) for index,residue in enumerate(peptide)]
                        prefix=[];running=0
                        for mass in masses[:-1]:running+=mass;prefix.append(running)
                        suffix=[];running=0
                        for mass in masses[:0:-1]:running+=mass;suffix.append(running)
                        ident=f'{protein["id"]}/{kind}:{start+1}-{end}:{tag}'
                        result.append({"id":ident,"kind":kind,"ions":prefix+suffix})
    return result
