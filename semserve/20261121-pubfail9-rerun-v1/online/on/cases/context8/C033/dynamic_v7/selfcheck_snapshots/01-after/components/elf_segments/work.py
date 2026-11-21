import struct


def compute(payload):
    """输出 [入口地址, [[地址,字节],…]]，按加载后的地址升序排列，包括 PT_LOAD 零填充。"""
    data = bytes.fromhex(payload["elf_hex"])
    entry = struct.unpack_from("<I", data, 24)[0]
    phoff = struct.unpack_from("<I", data, 28)[0]
    phentsize = struct.unpack_from("<H", data, 42)[0]
    phnum = struct.unpack_from("<H", data, 44)[0]

    segments = []
    for i in range(phnum):
        off = phoff + i * phentsize
        p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align = \
            struct.unpack_from("<IIIIIIII", data, off)
        if p_type != 1:  # PT_LOAD
            continue
        segments.append((p_vaddr, p_offset, p_filesz, p_memsz))

    # Build a byte map keyed by loaded address.
    mem = {}
    for vaddr, offset, filesz, memsz in segments:
        for j in range(memsz):
            addr = vaddr + j
            if j < filesz:
                mem[addr] = data[offset + j]
            else:
                mem[addr] = 0

    pairs = [[addr, mem[addr]] for addr in sorted(mem)]
    return [entry, pairs]
