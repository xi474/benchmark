import struct


def compute(payload):
    """输出 [入口地址, [[地址,字节],…]]，按加载后的地址升序排列，包括 PT_LOAD 零填充。"""
    data = bytes.fromhex(payload["elf_hex"])
    # ELF32 header: e_entry at offset 0x18, e_phoff at 0x1c,
    # e_phentsize at 0x2a, e_phnum at 0x2c.
    entry = struct.unpack_from("<I", data, 0x18)[0]
    phoff = struct.unpack_from("<I", data, 0x1C)[0]
    phentsize = struct.unpack_from("<H", data, 0x2A)[0]
    phnum = struct.unpack_from("<H", data, 0x2C)[0]

    segments = []
    for i in range(phnum):
        off = phoff + i * phentsize
        p_type, p_offset, p_vaddr, _paddr, p_filesz, p_memsz, _flags, _align = \
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
