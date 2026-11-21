def _u32(x):
    return x & 0xFFFFFFFF


def _s32(x):
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x >= 0x80000000 else x


def _signext(x, bits):
    sign = 1 << (bits - 1)
    x &= (1 << bits) - 1
    return x - (1 << bits) if x & sign else x


def combine(payload, left, right):
    entry, segments = left
    file_map, stdin_bytes = right

    mem = {}
    for addr, byte in segments:
        mem[addr] = byte

    regs = [0] * 32
    sp = payload.get("stack_pointer")
    regs[29] = sp if sp is not None else 0x7FFF0000
    hi = 0
    lo = 0

    files = {name: list(bytes.fromhex(h)) for name, h in payload.get("files", {}).items()}
    stdin_data = list(stdin_bytes)
    stdout_data = []
    stderr_data = []
    fds = {
        0: ["stdin", stdin_data, 0],
        1: ["stdout", stdout_data, 0],
        2: ["stderr", stderr_data, 0],
    }
    next_fd = 3

    syscalls = []
    inspect = payload.get("inspect", [])
    max_steps = payload.get("max_steps", 20000)

    pc = entry
    steps = 0
    exit_code = 0

    def read_mem(addr, n):
        return [mem.get(_u32(addr + i), 0) for i in range(n)]

    def write_mem(addr, data):
        for i, b in enumerate(data):
            mem[_u32(addr + i)] = b & 0xFF

    def load_word(addr):
        b = read_mem(addr, 4)
        return b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)

    def load_half(addr):
        b = read_mem(addr, 2)
        return b[0] | (b[1] << 8)

    def load_byte(addr):
        return read_mem(addr, 1)[0]

    def store_word(addr, val):
        write_mem(addr, [val & 0xFF, (val >> 8) & 0xFF, (val >> 16) & 0xFF, (val >> 24) & 0xFF])

    def store_half(addr, val):
        write_mem(addr, [val & 0xFF, (val >> 8) & 0xFF])

    def store_byte(addr, val):
        write_mem(addr, [val & 0xFF])

    def do_syscall():
        nonlocal exit_code, next_fd
        num = regs[2]
        a0 = regs[4]
        a1 = regs[5]
        a2 = regs[6]
        syscalls.append({"number": num, "args": [a0, a1, a2]})
        result = 0
        if num == 4001:
            exit_code = a0 & 0xFF
            return True
        elif num == 4003:
            fd = a0
            buf = a1
            n = a2
            entry_fd = fds[fd]
            kind, data, off = entry_fd
            avail = len(data) - off
            count = min(n, avail)
            chunk = data[off:off + count]
            write_mem(buf, chunk)
            entry_fd[2] = off + count
            result = count
        elif num == 4004:
            fd = a0
            buf = a1
            n = a2
            chunk = read_mem(buf, n)
            entry_fd = fds[fd]
            entry_fd[1].extend(chunk)
            result = n
        elif num == 4005:
            filename = a0
            flags = a1
            mode = a2
            name_bytes = []
            i = 0
            while True:
                b = load_byte(filename + i)
                if b == 0:
                    break
                name_bytes.append(b)
                i += 1
            name = bytes(name_bytes).decode("utf-8")
            if flags == 0:
                data = list(files.get(name, []))
            elif flags == 1:
                data = []
                files[name] = data
            elif flags == 9:
                data = files.get(name, [])
                files[name] = data
            else:
                data = files.get(name, [])
            fd = next_fd
            next_fd += 1
            fds[fd] = ["file", data, 0]
            result = fd
        elif num == 4006:
            fd = a0
            if fd in fds:
                del fds[fd]
            result = 0
        regs[2] = _u32(result)
        regs[7] = 0
        return False

    def execute(instr):
        opcode = instr >> 26
        rs = (instr >> 21) & 0x1F
        rt = (instr >> 16) & 0x1F
        rd = (instr >> 11) & 0x1F
        shamt = (instr >> 6) & 0x1F
        funct = instr & 0x3F
        imm = instr & 0xFFFF
        if opcode == 0:
            if funct == 0x00:
                regs[rd] = _u32(regs[rt] << shamt)
            elif funct == 0x02:
                regs[rd] = _u32(regs[rt] >> shamt)
            elif funct == 0x03:
                regs[rd] = _u32(_s32(regs[rt]) >> shamt)
            elif funct == 0x10:
                regs[rd] = hi
            elif funct == 0x11:
                hi = regs[rs]
            elif funct == 0x12:
                regs[rd] = lo
            elif funct == 0x13:
                lo = regs[rs]
            elif funct == 0x18:
                prod = _s32(regs[rs]) * _s32(regs[rt]) & 0xFFFFFFFFFFFFFFFF
                hi = _u32(prod >> 32)
                lo = _u32(prod)
            elif funct == 0x19:
                prod = regs[rs] * regs[rt] & 0xFFFFFFFFFFFFFFFF
                hi = _u32(prod >> 32)
                lo = _u32(prod)
            elif funct == 0x1A:
                a = _s32(regs[rs]); b = _s32(regs[rt])
                q = int(a / b) if b else 0
                lo = _u32(q); hi = _u32(a - q * b)
            elif funct == 0x1B:
                a = regs[rs]; b = regs[rt]
                q = a // b if b else 0
                lo = _u32(q); hi = _u32(a - q * b)
            elif funct == 0x20:
                regs[rd] = _u32(regs[rs] + regs[rt])
            elif funct == 0x21:
                regs[rd] = _u32(regs[rs] + regs[rt])
            elif funct == 0x22:
                regs[rd] = _u32(regs[rs] - regs[rt])
            elif funct == 0x23:
                regs[rd] = _u32(regs[rs] - regs[rt])
            elif funct == 0x24:
                regs[rd] = regs[rs] & regs[rt]
            elif funct == 0x25:
                regs[rd] = regs[rs] | regs[rt]
            elif funct == 0x26:
                regs[rd] = regs[rs] ^ regs[rt]
            elif funct == 0x27:
                regs[rd] = _u32(~(regs[rs] | regs[rt]))
            elif funct == 0x2A:
                regs[rd] = 1 if _s32(regs[rs]) < _s32(regs[rt]) else 0
            elif funct == 0x2B:
                regs[rd] = 1 if regs[rs] < regs[rt] else 0
        elif opcode == 0x08:
            regs[rt] = _u32(regs[rs] + _signext(imm, 16))
        elif opcode == 0x09:
            regs[rt] = _u32(regs[rs] + _signext(imm, 16))
        elif opcode == 0x0A:
            regs[rt] = 1 if _s32(regs[rs]) < _signext(imm, 16) else 0
        elif opcode == 0x0B:
            regs[rt] = 1 if regs[rs] < _u32(_signext(imm, 16)) else 0
        elif opcode == 0x0C:
            regs[rt] = regs[rs] & imm
        elif opcode == 0x0D:
            regs[rt] = regs[rs] | imm
        elif opcode == 0x0E:
            regs[rt] = regs[rs] ^ imm
        elif opcode == 0x0F:
            regs[rt] = _u32(imm << 16)
        elif opcode == 0x20:
            regs[rt] = _u32(_signext(load_byte(regs[rs] + _signext(imm, 16)), 8))
        elif opcode == 0x24:
            regs[rt] = load_byte(regs[rs] + _signext(imm, 16))
        elif opcode == 0x21:
            regs[rt] = _u32(_signext(load_half(regs[rs] + _signext(imm, 16)), 16))
        elif opcode == 0x25:
            regs[rt] = load_half(regs[rs] + _signext(imm, 16))
        elif opcode == 0x23:
            regs[rt] = load_word(regs[rs] + _signext(imm, 16))
        elif opcode == 0x28:
            store_byte(regs[rs] + _signext(imm, 16), regs[rt])
        elif opcode == 0x29:
            store_half(regs[rs] + _signext(imm, 16), regs[rt])
        elif opcode == 0x2B:
            store_word(regs[rs] + _signext(imm, 16), regs[rt])
        regs[0] = 0

    while steps < max_steps:
        instr = load_word(pc)
        opcode = instr >> 26
        rs = (instr >> 21) & 0x1F
        rt = (instr >> 16) & 0x1F
        rd = (instr >> 11) & 0x1F
        shamt = (instr >> 6) & 0x1F
        funct = instr & 0x3F
        imm = instr & 0xFFFF
        target = instr & 0x03FFFFFF

        next_pc = _u32(pc + 4)
        delay_pc = next_pc
        jump = False
        link = False
        link_reg = 31
        is_syscall = False

        if opcode == 0:
            if funct == 0x08:
                jump = True
                next_pc = regs[rs]
            elif funct == 0x09:
                jump = True
                link = True
                link_reg = rd
                next_pc = regs[rs]
            elif funct == 0x0C:
                is_syscall = True
            else:
                execute(instr)
        elif opcode == 0x02:
            jump = True
            next_pc = (next_pc & 0xF0000000) | (target << 2)
        elif opcode == 0x03:
            jump = True
            link = True
            next_pc = (next_pc & 0xF0000000) | (target << 2)
        elif opcode == 0x04:
            if regs[rs] == regs[rt]:
                next_pc = _u32(pc + 4 + (_signext(imm, 16) << 2))
        elif opcode == 0x05:
            if regs[rs] != regs[rt]:
                next_pc = _u32(pc + 4 + (_signext(imm, 16) << 2))
        elif opcode == 0x06:
            if _s32(regs[rs]) <= 0:
                next_pc = _u32(pc + 4 + (_signext(imm, 16) << 2))
        elif opcode == 0x07:
            if _s32(regs[rs]) > 0:
                next_pc = _u32(pc + 4 + (_signext(imm, 16) << 2))
        else:
            execute(instr)

        regs[0] = 0

        if link:
            regs[link_reg] = _u32(pc + 8)

        delay_instr = load_word(delay_pc)
        execute(delay_instr)

        steps += 1

        if is_syscall:
            if do_syscall():
                steps += 1
                break

        pc = next_pc

    result = {
        "exit_code": exit_code,
        "registers": [regs[i] & 0xFFFFFFFF for i in range(32)],
        "hi": hi & 0xFFFFFFFF,
        "lo": lo & 0xFFFFFFFF,
        "steps": steps,
        "stdout_hex": bytes(stdout_data).hex(),
        "stderr_hex": bytes(stderr_data).hex(),
        "files": {name: bytes(data).hex() for name, data in files.items()},
        "inspect": [],
        "syscalls": syscalls,
    }
    for item in inspect:
        addr = item["address"]
        length = item["length"]
        data = read_mem(addr, length)
        result["inspect"].append({"address": addr, "hex": bytes(data).hex()})
    return result
