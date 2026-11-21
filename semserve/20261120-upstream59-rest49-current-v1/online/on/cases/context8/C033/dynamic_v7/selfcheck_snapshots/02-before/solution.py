"""MIPS32 ELF loader + interpreter subset with delay slots and file I/O."""

import json
import struct

MASK32 = 0xFFFFFFFF


def _u32(x):
    return x & MASK32


def _s32(x):
    x &= MASK32
    return x - 0x100000000 if x >= 0x80000000 else x


def _sign_ext(value, bits):
    sign = 1 << (bits - 1)
    return (value & (sign - 1)) - (value & sign)


def _sign_ext16(v):
    return _sign_ext(v, 16)


class Memory:
    def __init__(self):
        self.data = bytearray()

    def _ensure(self, addr, size):
        end = addr + size
        if end > len(self.data):
            self.data.extend(b"\x00" * (end - len(self.data)))

    def read(self, addr, size):
        self._ensure(addr, size)
        return bytes(self.data[addr:addr + size])

    def write(self, addr, data):
        self._ensure(addr, len(data))
        self.data[addr:addr + len(data)] = data


class FileSystem:
    def __init__(self, files, stdin_hex):
        self.files = {}
        for name, hexstr in files.items():
            self.files[name] = bytes.fromhex(hexstr)
        self.stdin = bytes.fromhex(stdin_hex) if stdin_hex else b""
        self.stdin_pos = 0
        self.stdout = bytearray()
        self.stderr = bytearray()
        self.fds = {}
        self.next_fd = 3
        self.fds[0] = {"kind": "stdin"}
        self.fds[1] = {"kind": "stdout"}
        self.fds[2] = {"kind": "stderr"}

    def read_stdin(self, n):
        data = self.stdin[self.stdin_pos:self.stdin_pos + n]
        self.stdin_pos += len(data)
        return data

    def open(self, filename, flags, mode):
        name = filename.decode("utf-8")
        if flags == 0:
            data = self.files.get(name, b"")
        elif flags == 1:
            data = b""
        elif flags == 9:
            data = self.files.get(name, b"")
        else:
            data = self.files.get(name, b"")
        fd = self.next_fd
        self.next_fd += 1
        pos = len(data) if flags == 9 else 0
        self.fds[fd] = {"kind": "file", "name": name, "data": bytearray(data), "pos": pos}
        return fd

    def read(self, fd, n):
        entry = self.fds[fd]
        if entry["kind"] == "stdin":
            return self.read_stdin(n)
        data = entry["data"]
        chunk = bytes(data[entry["pos"]:entry["pos"] + n])
        entry["pos"] += len(chunk)
        return chunk

    def write(self, fd, data):
        entry = self.fds[fd]
        if entry["kind"] == "stdout":
            self.stdout.extend(data)
        elif entry["kind"] == "stderr":
            self.stderr.extend(data)
        else:
            d = entry["data"]
            pos = entry["pos"]
            if pos + len(data) > len(d):
                d.extend(b"\x00" * (pos + len(data) - len(d)))
            d[pos:pos + len(data)] = data
            entry["pos"] = pos + len(data)

    def close(self, fd):
        if fd in self.fds and fd >= 3:
            del self.fds[fd]

    def final_files(self):
        result = {}
        for fd, entry in self.fds.items():
            if entry["kind"] == "file":
                result[entry["name"]] = bytes(entry["data"]).hex()
        return result


def _load_elf(elf_bytes):
    if elf_bytes[:4] != b"\x7fELF":
        raise ValueError("not ELF")
    e_entry = struct.unpack_from("<I", elf_bytes, 0x18)[0]
    e_phoff = struct.unpack_from("<I", elf_bytes, 0x1C)[0]
    e_phentsize = struct.unpack_from("<H", elf_bytes, 0x2A)[0]
    e_phnum = struct.unpack_from("<H", elf_bytes, 0x2C)[0]
    mem = Memory()
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type = struct.unpack_from("<I", elf_bytes, off)[0]
        if p_type != 1:  # PT_LOAD
            continue
        p_offset = struct.unpack_from("<I", elf_bytes, off + 4)[0]
        p_vaddr = struct.unpack_from("<I", elf_bytes, off + 8)[0]
        p_filesz = struct.unpack_from("<I", elf_bytes, off + 16)[0]
        p_memsz = struct.unpack_from("<I", elf_bytes, off + 20)[0]
        if p_filesz:
            mem.write(p_vaddr, elf_bytes[p_offset:p_offset + p_filesz])
        if p_memsz > p_filesz:
            mem.write(p_vaddr + p_filesz, b"\x00" * (p_memsz - p_filesz))
    return mem, e_entry


def _decode(instr):
    op = (instr >> 26) & 0x3F
    rs = (instr >> 21) & 0x1F
    rt = (instr >> 16) & 0x1F
    rd = (instr >> 11) & 0x1F
    shamt = (instr >> 6) & 0x1F
    funct = instr & 0x3F
    imm = instr & 0xFFFF
    target = instr & 0x3FFFFFF
    return op, rs, rt, rd, shamt, funct, imm, target


def transform(payload):
    elf_hex = payload["elf_hex"]
    elf_bytes = bytes.fromhex(elf_hex)
    mem, entry = _load_elf(elf_bytes)

    files = payload.get("files", {})
    stdin_hex = payload.get("stdin_hex", "")
    inspect = payload.get("inspect", [])
    max_steps = payload.get("max_steps", 20000)
    stack_pointer = payload.get("stack_pointer", 0x7FFF0000)

    fs = FileSystem(files, stdin_hex)

    regs = [0] * 32
    regs[29] = _u32(stack_pointer)
    hi = 0
    lo = 0
    pc = entry

    syscalls = []
    steps = 0
    exit_code = 0

    def read_word(addr):
        return struct.unpack_from("<I", mem.read(addr, 4), 0)[0]

    def read_byte(addr):
        return mem.read(addr, 1)[0]

    def read_half(addr):
        return struct.unpack_from("<H", mem.read(addr, 2), 0)[0]

    def write_byte(addr, val):
        mem.write(addr, bytes([val & 0xFF]))

    def write_half(addr, val):
        mem.write(addr, struct.pack("<H", val & 0xFFFF))

    def write_word(addr, val):
        mem.write(addr, struct.pack("<I", val & MASK32))

    def read_cstr(addr):
        out = bytearray()
        while True:
            b = read_byte(addr)
            if b == 0:
                break
            out.append(b)
            addr += 1
        return bytes(out)

    def do_syscall():
        nonlocal exit_code
        number = regs[2]
        a0 = regs[4]
        a1 = regs[5]
        a2 = regs[6]
        syscalls.append({"number": number, "args": [a0, a1, a2]})
        if number == 4001:
            exit_code = a0 & 0xFF
            regs[7] = 0
            return True
        elif number == 4003:
            data = fs.read(a0, a1)
            mem.write(a1, data)
            regs[2] = len(data)
            regs[7] = 0
        elif number == 4004:
            data = mem.read(a1, a2)
            fs.write(a0, data)
            regs[2] = len(data)
            regs[7] = 0
        elif number == 4005:
            name = read_cstr(a0)
            fd = fs.open(name, a1, a2)
            regs[2] = fd
            regs[7] = 0
        elif number == 4006:
            fs.close(a0)
            regs[2] = 0
            regs[7] = 0
        return False

    def exec_instr(instr):
        op, rs, rt, rd, shamt, funct, imm, target = _decode(instr)
        if op == 0:
            if funct == 0x00:  # sll
                regs[rd] = _u32(regs[rt] << shamt)
            elif funct == 0x02:  # srl
                regs[rd] = _u32(regs[rt] >> shamt)
            elif funct == 0x03:  # sra
                regs[rd] = _u32(_s32(regs[rt]) >> shamt)
            elif funct == 0x20:  # add
                regs[rd] = _u32(regs[rs] + regs[rt])
            elif funct == 0x21:  # addu
                regs[rd] = _u32(regs[rs] + regs[rt])
            elif funct == 0x22:  # sub
                regs[rd] = _u32(regs[rs] - regs[rt])
            elif funct == 0x23:  # subu
                regs[rd] = _u32(regs[rs] - regs[rt])
            elif funct == 0x24:  # and
                regs[rd] = regs[rs] & regs[rt]
            elif funct == 0x25:  # or
                regs[rd] = regs[rs] | regs[rt]
            elif funct == 0x26:  # xor
                regs[rd] = regs[rs] ^ regs[rt]
            elif funct == 0x27:  # nor
                regs[rd] = _u32(~(regs[rs] | regs[rt]))
            elif funct == 0x2A:  # slt
                regs[rd] = 1 if _s32(regs[rs]) < _s32(regs[rt]) else 0
            elif funct == 0x2B:  # sltu
                regs[rd] = 1 if regs[rs] < regs[rt] else 0
            elif funct == 0x10:  # mfhi
                regs[rd] = hi
            elif funct == 0x12:  # mflo
                regs[rd] = lo
            elif funct == 0x11:  # mthi
                hi = regs[rs]
            elif funct == 0x13:  # mtlo
                lo = regs[rs]
            elif funct == 0x18:  # mult
                prod = _s32(regs[rs]) * _s32(regs[rt])
                lo = _u32(prod)
                hi = _u32(prod >> 32)
            elif funct == 0x19:  # multu
                prod = regs[rs] * regs[rt]
                lo = _u32(prod)
                hi = _u32(prod >> 32)
            elif funct == 0x1A:  # div
                a = _s32(regs[rs])
                b = _s32(regs[rt])
                q = int(a / b)
                lo = _u32(q)
                hi = _u32(a - q * b)
            elif funct == 0x1B:  # divu
                a = regs[rs]
                b = regs[rt]
                lo = _u32(a // b)
                hi = _u32(a % b)
        elif op == 0x08:  # addi
            regs[rt] = _u32(regs[rs] + _sign_ext16(imm))
        elif op == 0x09:  # addiu
            regs[rt] = _u32(regs[rs] + _sign_ext16(imm))
        elif op == 0x0A:  # slti
            regs[rt] = 1 if _s32(regs[rs]) < _sign_ext16(imm) else 0
        elif op == 0x0B:  # sltiu
            regs[rt] = 1 if regs[rs] < _u32(_sign_ext16(imm)) else 0
        elif op == 0x0C:  # andi
            regs[rt] = regs[rs] & imm
        elif op == 0x0D:  # ori
            regs[rt] = regs[rs] | imm
        elif op == 0x0E:  # xori
            regs[rt] = regs[rs] ^ imm
        elif op == 0x0F:  # lui
            regs[rt] = _u32(imm << 16)
        elif op == 0x20:  # lb
            regs[rt] = _u32(_sign_ext(read_byte(regs[rs] + _sign_ext16(imm)), 8))
        elif op == 0x24:  # lbu
            regs[rt] = read_byte(regs[rs] + _sign_ext16(imm))
        elif op == 0x21:  # lh
            regs[rt] = _u32(_sign_ext(read_half(regs[rs] + _sign_ext16(imm)), 16))
        elif op == 0x25:  # lhu
            regs[rt] = read_half(regs[rs] + _sign_ext16(imm))
        elif op == 0x23:  # lw
            regs[rt] = read_word(regs[rs] + _sign_ext16(imm))
        elif op == 0x28:  # sb
            write_byte(regs[rs] + _sign_ext16(imm), regs[rt])
        elif op == 0x29:  # sh
            write_half(regs[rs] + _sign_ext16(imm), regs[rt])
        elif op == 0x2B:  # sw
            write_word(regs[rs] + _sign_ext16(imm), regs[rt])
        regs[0] = 0

    while steps < max_steps:
        instr = read_word(pc)
        op, rs, rt, rd, shamt, funct, imm, target = _decode(instr)
        pc_next = pc + 4
        delay = None

        if op == 0:
            if funct == 0x08:  # jr
                delay = regs[rs]
            elif funct == 0x09:  # jalr
                regs[rd] = pc + 8
                delay = regs[rs]
            elif funct == 0x0C:  # syscall
                if do_syscall():
                    steps += 1
                    break
        elif op == 0x02:  # j
            delay = (pc_next & 0xF0000000) | (target << 2)
        elif op == 0x03:  # jal
            regs[31] = pc + 8
            delay = (pc_next & 0xF0000000) | (target << 2)
        elif op in (0x04, 0x05, 0x06, 0x07):
            a = regs[rs]
            b = regs[rt] if op in (0x04, 0x05) else 0
            taken = False
            if op == 0x04:
                taken = a == b
            elif op == 0x05:
                taken = a != b
            elif op == 0x06:
                taken = _s32(a) <= 0
            elif op == 0x07:
                taken = _s32(a) > 0
            if taken:
                delay = pc_next + (_sign_ext16(imm) << 2)

        # Execute current instruction's non-control effects
        exec_instr(instr)
        steps += 1

        if delay is not None:
            dinstr = read_word(pc_next)
            exec_instr(dinstr)
            steps += 1
            pc = delay
        else:
            pc = pc_next

    inspect_out = []
    for item in inspect:
        addr = item["address"]
        length = item["length"]
        inspect_out.append({"address": addr, "hex": mem.read(addr, length).hex()})

    return {
        "exit_code": exit_code,
        "registers": [_u32(r) for r in regs],
        "hi": _u32(hi),
        "lo": _u32(lo),
        "steps": steps,
        "stdout_hex": bytes(fs.stdout).hex(),
        "stderr_hex": bytes(fs.stderr).hex(),
        "files": fs.final_files(),
        "inspect": inspect_out,
        "syscalls": syscalls,
    }


def load_payload(input_path):
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_component(input_path, output_path):
    payload = load_payload(input_path)
    result = transform(payload)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f)
    return result
