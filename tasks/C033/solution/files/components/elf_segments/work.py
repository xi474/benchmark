import struct
def compute(payload):
    image=bytes.fromhex(payload['elf_hex']);memory={}
    entry=struct.unpack_from('<I',image,24)[0];phoff=struct.unpack_from('<I',image,28)[0]
    phsize,phnum=struct.unpack_from('<HH',image,42)
    for i in range(phnum):
        kind,offset,vaddr,paddr,filesz,memsz,flags,align=struct.unpack_from('<8I',image,phoff+i*phsize)
        if kind==1:
            for j,b in enumerate(image[offset:offset+filesz]):memory[vaddr+j]=b
            for j in range(filesz,memsz):memory[vaddr+j]=0
    return [entry,sorted(memory.items())]
