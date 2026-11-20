"""Author-only little-endian MIPS32 ELF interpreter with Linux-style I/O."""
import struct


def transform(payload):
    image=bytes.fromhex(payload['elf_hex']);memory={}
    entry=struct.unpack_from('<I',image,24)[0];phoff=struct.unpack_from('<I',image,28)[0]
    phsize,phnum=struct.unpack_from('<HH',image,42)
    for i in range(phnum):
        kind,offset,vaddr,paddr,filesz,memsz,flags,align=struct.unpack_from('<8I',image,phoff+i*phsize)
        if kind==1:
            for j,b in enumerate(image[offset:offset+filesz]):memory[vaddr+j]=b
            for j in range(filesz,memsz):memory[vaddr+j]=0
    regs=[0]*32;regs[29]=payload.get('stack_pointer',0x7fff0000);hi=lo=0;pc=entry;pending=None
    files={k:bytearray.fromhex(v) for k,v in payload.get('files',{}).items()}
    fd={0:[bytearray.fromhex(payload.get('stdin_hex','')),0,None],1:[bytearray(),0,None],2:[bytearray(),0,None]}
    nextfd=3;exit_code=None;steps=0;calls=[]
    u=lambda x:x&0xffffffff
    s=lambda x:x-0x100000000 if x&0x80000000 else x
    def load(addr,size):return sum(memory.get(u(addr+i),0)<<(8*i) for i in range(size))
    def store(addr,size,value):
        for i in range(size):memory[u(addr+i)]=(value>>(8*i))&255
    def cname(addr):
        b=[]
        while memory.get(addr,0):b.append(memory[addr]);addr+=1
        return bytes(b).decode('utf-8')
    while exit_code is None:
        steps+=1
        if steps>payload.get('max_steps',20000):raise RuntimeError('legal program exceeded declared bound')
        word=load(pc,4);op=word>>26;rs=(word>>21)&31;rt=(word>>16)&31;rd=(word>>11)&31;sh=(word>>6)&31;fn=word&63
        imm=word&65535;simm=imm-65536 if imm&32768 else imm
        oldpending=pending;pending=None;at=pc
        if op==0:
            if fn==0:regs[rd]=u(regs[rt]<<sh)
            elif fn==2:regs[rd]=regs[rt]>>sh
            elif fn==3:regs[rd]=u(s(regs[rt])>>sh)
            elif fn==8:pending=regs[rs]
            elif fn==9:regs[rd]=u(pc+8);pending=regs[rs]
            elif fn in (32,33):regs[rd]=u(regs[rs]+regs[rt])
            elif fn in (34,35):regs[rd]=u(regs[rs]-regs[rt])
            elif fn==36:regs[rd]=regs[rs]&regs[rt]
            elif fn==37:regs[rd]=regs[rs]|regs[rt]
            elif fn==38:regs[rd]=regs[rs]^regs[rt]
            elif fn==39:regs[rd]=u(~(regs[rs]|regs[rt]))
            elif fn==42:regs[rd]=int(s(regs[rs])<s(regs[rt]))
            elif fn==43:regs[rd]=int(regs[rs]<regs[rt])
            elif fn==16:regs[rd]=hi
            elif fn==18:regs[rd]=lo
            elif fn==17:hi=regs[rs]
            elif fn==19:lo=regs[rs]
            elif fn in (24,25):
                val=(s(regs[rs])*s(regs[rt]) if fn==24 else regs[rs]*regs[rt])&0xffffffffffffffff
                hi,lo=(val>>32)&0xffffffff,val&0xffffffff
            elif fn in (26,27):
                a,b=(s(regs[rs]),s(regs[rt])) if fn==26 else (regs[rs],regs[rt])
                q=abs(a)//abs(b)*(1 if a*b>=0 else -1);lo=u(q);hi=u(a-q*b)
            elif fn==12:
                number=regs[2];a0,a1,a2=regs[4:7]
                calls.append(dict(number=number,args=[a0,a1,a2]))
                if number==4001:exit_code=a0&255
                elif number==4005:
                    name=cname(a0);flags=a1
                    if flags==1:files[name]=bytearray()
                    if flags==9:files.setdefault(name,bytearray())
                    buf=files[name];position=len(buf) if flags==9 else 0
                    fd[nextfd]=[buf,position,name];regs[2]=nextfd;nextfd+=1
                elif number==4006:del fd[a0];regs[2]=0
                elif number==4003:
                    handle=fd[a0];chunk=handle[0][handle[1]:handle[1]+a2];handle[1]+=len(chunk)
                    for i,b in enumerate(chunk):memory[a1+i]=b
                    regs[2]=len(chunk)
                elif number==4004:
                    chunk=bytes(memory.get(a1+i,0) for i in range(a2));handle=fd[a0]
                    if a0 in (1,2):handle[0].extend(chunk)
                    else:
                        end=handle[1]+len(chunk)
                        if end>len(handle[0]):handle[0].extend(b'\0'*(end-len(handle[0])))
                        handle[0][handle[1]:end]=chunk;handle[1]=end
                    regs[2]=len(chunk)
                else:raise ValueError('syscall outside public subset')
                regs[7]=0
            else:raise ValueError('SPECIAL outside public subset')
        elif op in (2,3):
            if op==3:regs[31]=u(pc+8)
            pending=((pc+4)&0xf0000000)|((word&0x3ffffff)<<2)
        elif op in (4,5,6,7):
            take={4:regs[rs]==regs[rt],5:regs[rs]!=regs[rt],6:s(regs[rs])<=0,7:s(regs[rs])>0}[op]
            if take:pending=u(pc+4+(simm<<2))
        elif op in (8,9):regs[rt]=u(regs[rs]+simm)
        elif op==10:regs[rt]=int(s(regs[rs])<simm)
        elif op==11:regs[rt]=int(regs[rs]<u(simm))
        elif op==12:regs[rt]=regs[rs]&imm
        elif op==13:regs[rt]=regs[rs]|imm
        elif op==14:regs[rt]=regs[rs]^imm
        elif op==15:regs[rt]=imm<<16
        elif op in (32,33,35,36,37):
            size={32:1,33:2,35:4,36:1,37:2}[op];value=load(u(regs[rs]+simm),size)
            if op in (32,33) and value&(1<<(size*8-1)):value-=1<<(size*8)
            regs[rt]=u(value)
        elif op in (40,41,43):store(u(regs[rs]+simm),{40:1,41:2,43:4}[op],regs[rt])
        else:raise ValueError('opcode outside public subset')
        regs[0]=0;pc=oldpending if oldpending is not None else u(at+4)
    inspect=[dict(address=x['address'],hex=bytes(memory.get(x['address']+i,0) for i in range(x['length'])).hex())
             for x in payload.get('inspect',[])]
    return dict(exit_code=exit_code,registers=regs,hi=hi,lo=lo,steps=steps,
                stdout_hex=bytes(fd[1][0]).hex(),stderr_hex=bytes(fd[2][0]).hex(),
                files={k:bytes(v).hex() for k,v in sorted(files.items())},inspect=inspect,syscalls=calls)

from pathlib import Path
import json
def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def build_component(input_path,output_path):
    value=transform(load_payload(input_path))
    p=Path(output_path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return value
