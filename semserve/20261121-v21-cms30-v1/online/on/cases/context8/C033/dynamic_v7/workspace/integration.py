"""MIPS32 interpreter integration for C033.

combine(payload, left, right) consumes the two component values:
  left  = [entry, [[address, byte], ...]]   (elf_segments)
  right = [files_map, stdin_bytes]          (io_buffers)
and produces the full business result JSON described in TASK.md.
"""

MASK32 = 0xFFFFFFFF


def _s32(v):
    v &= MASK32
    return v - (1 << 32) if v & (1 << 31) else v


def _u32(v):
    return v & MASK32


def _sign_extend(v, bits):
    v &= (1 << bits) - 1
    if v & (1 << (bits - 1)):
        v -= 1 << bits
    return v


class _Machine:
    def __init__(self, payload, left, right):
        entry, pairs = left
        self.entry = entry
        self.mem = {}
        for addr, byte in pairs:
            self.mem[addr & MASK32] = byte & 0xFF

        files_map, stdin_bytes = right
        self.files = {name: list(data) for name, data in files_map.items()}
        self.stdin = list(stdin_bytes)

        self.regs = [0] * 32
        self.hi = 0
        self.lo = 0
        sp = payload.get("stack_pointer")
        self.regs[29] = _u32(sp) if sp is not None else 0x7FFF0000

        self.inspect = payload.get("inspect") or []
        self.max_steps = payload.get("max_steps", 20000)

        self.stdout = bytearray()
        self.stderr = bytearray()
        self.syscalls = []
        self.steps = 0
        self.exit_code = None

        self.fds = {
            0: {"kind": "stdin", "pos": 0},
            1: {"kind": "stdout"},
            2: {"kind": "stderr"},
        }
        self.next_fd = 3

    def read_byte(self, addr):
        return self.mem.get(addr & MASK32, 0)

    def read_half(self, addr):
        a = addr & MASK32
        return self.read_byte(a) | (self.read_byte(a + 1) << 8)

    def read_word(self, addr):
        a = addr & MASK32
        return (
            self.read_byte(a)
            | (self.read_byte(a + 1) << 8)
            | (self.read_byte(a + 2) << 16)
            | (self.read_byte(a + 3) << 24)
        )

    def write_byte(self, addr, val):
        self.mem[addr & MASK32] = val & 0xFF

    def write_half(self, addr, val):
        a = addr & MASK32
        self.write_byte(a, val & 0xFF)
        self.write_byte(a + 1, (val >> 8) & 0xFF)

    def write_word(self, addr, val):
        a = addr & MASK32
        self.write_byte(a, val & 0xFF)
        self.write_byte(a + 1, (val >> 8) & 0xFF)
        self.write_byte(a + 2, (val >> 16) & 0xFF)
        self.write_byte(a + 3, (val >> 24) & 0xFF)

    def syscall(self):
        number = self.regs[2]
        a0 = self.regs[4]
        a1 = self.regs[5]
        a2 = self.regs[6]
        self.syscalls.append({"number": number, "args": [a0, a1, a2]})
        result = 0
        if number == 4001:
            self.exit_code = a0 & 0xFF
        elif number == 4003:
            fd = a0
            buf = a1
            n = a2
            data = self._read_fd(fd, n)
            for i, b in enumerate(data):
                self.write_byte(buf + i, b)
            result = len(data)
        elif number == 4004:
            fd = a0
            buf = a1
            n = a2
            data = bytes(self.read_byte(buf + i) for i in range(n))
            self._write_fd(fd, data)
            result = n
        elif number == 4005:
            filename = self._read_cstring(a0)
            flags = a1
            self._open(filename, flags)
            result = self.next_fd - 1
        elif number == 4006:
            fd = a0
            if fd in self.fds and fd >= 3:
                del self.fds[fd]
        else:
            raise RuntimeError("unknown syscall %d" % number)
        self.regs[2] = _u32(result)
        self.regs[7] = 0

    def _read_cstring(self, addr):
        out = bytearray()
        a = addr & MASK32
        while True:
            b = self.read_byte(a)
            if b == 0:
                break
            out.append(b)
            a = (a + 1) & MASK32
        return bytes(out).decode("utf-8")

    def _read_fd(self, fd, n):
        if fd == 0:
            pos = self.fds[0]["pos"]
            data = self.stdin[pos:pos + n]
            self.fds[0]["pos"] = pos + len(data)
            return data
        if fd in self.fds and self.fds[fd]["kind"] == "file":
            f = self.fds[fd]
            pos = f["pos"]
            data = f["data"][pos:pos + n]
            f["pos"] = pos + len(data)
            return data
        return []

    def _write_fd(self, fd, data):
        if fd == 1:
            self.stdout.extend(data)
        elif fd == 2:
            self.stderr.extend(data)
        elif fd in self.fds and self.fds[fd]["kind"] == "file":
            f = self.fds[fd]
            pos = f["pos"]
            f["data"][pos:pos + len(data)] = list(data)
            f["pos"] = pos + len(data)

    def _open(self, filename, flags):
        if flags == 0:
            data = list(self.files.get(filename, []))
        elif flags == 1:
            data = []
        elif flags == 9:
            data = list(self.files.get(filename, []))
        else:
            raise RuntimeError("unknown open flags %d" % flags)
        fd = self.next_fd
        self.next_fd += 1
        self.fds[fd] = {"kind": "file", "name": filename, "data": data, "pos": 0}
        if flags == 9:
            self.fds[fd]["pos"] = len(data)

    def run(self):
        pc = self.entry & MASK32
        while self.exit_code is None:
            if self.steps >= self.max_steps:
                raise RuntimeError("max_steps exceeded")
            self.steps += 1
            instr = self.read_word(pc)
            pc = self.execute(instr, pc)
        return pc

    def execute(self, instr, pc):
        op = (instr >> 26) & 0x3F
        rs = (instr >> 21) & 0x1F
        rt = (instr >> 16) & 0x1F
        rd = (instr >> 11) & 0x1F
        shamt = (instr >> 6) & 0x1F
        funct = instr & 0x3F
        imm = instr & 0xFFFF
        target = instr & 0x3FFFFFF

        next_pc = (pc + 4) & MASK32

        if op == 0:
            return self.execute_rtype(funct, rs, rt, rd, shamt, pc, next_pc)
        elif op in (0x02, 0x03):
            return self.execute_j(op, target, pc, next_pc)
        elif op in (0x04, 0x05, 0x06, 0x07):
            return self.execute_branch(op, rs, rt, imm, pc, next_pc)
        elif op in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F):
            return self.execute_imm(op, rs, rt, imm, pc, next_pc)
        elif op in (0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B):
            return self.execute_mem(op, rs, rt, imm, pc, next_pc)
        else:
            raise RuntimeError("unknown opcode 0x%02X at 0x%08X" % (op, pc))

    def execute_rtype(self, funct, rs, rt, rd, shamt, pc, next_pc):
        s = self.regs[rs]
        t = self.regs[rt]
        if funct == 0x00:
            self._set(rd, _u32(t << shamt))
        elif funct == 0x02:
            self._set(rd, _u32(t >> shamt))
        elif funct == 0x03:
            self._set(rd, _u32(_s32(t) >> shamt))
        elif funct == 0x08:
            return self.regs[rs] & MASK32
        elif funct == 0x09:
            self._set(rd, next_pc)
            return self.regs[rs] & MASK32
        elif funct == 0x20:
            self._set(rd, _u32(s + t))
        elif funct == 0x21:
            self._set(rd, _u32(s + t))
        elif funct == 0x22:
            self._set(rd, _u32(s - t))
        elif funct == 0x23:
            self._set(rd, _u32(s - t))
        elif funct == 0x24:
            self._set(rd, s & t)
        elif funct == 0x25:
            self._set(rd, s | t)
        elif funct == 0x26:
            self._set(rd, s ^ t)
        elif funct == 0x27:
            self._set(rd, _u32(~(s | t)))
        elif funct == 0x2A:
            self._set(rd, 1 if _s32(s) < _s32(t) else 0)
        elif funct == 0x2B:
            self._set(rd, 1 if s < t else 0)
        elif funct == 0x10:
            self._set(rd, self.hi)
        elif funct == 0x12:
            self._set(rd, self.lo)
        elif funct == 0x11:
            self.hi = s
        elif funct == 0x13:
            self.lo = s
        elif funct == 0x18:
            prod = _s32(s) * _s32(t)
            self.lo = _u32(prod)
            self.hi = _u32(prod >> 32)
        elif funct == 0x19:
            prod = s * t
            self.lo = _u32(prod)
            self.hi = _u32(prod >> 32)
        elif funct == 0x1A:
            a = _s32(s)
            b = _s32(t)
            q = int(a / b) if b != 0 else 0
            r = a - q * b
            self.lo = _u32(q)
            self.hi = _u32(r)
        elif funct == 0x1B:
            b = t
            q = s // b if b != 0 else 0
            r = s - q * b
            self.lo = _u32(q)
            self.hi = _u32(r)
        elif funct == 0x0C:
            self.syscall()
        else:
            raise RuntimeError("unknown funct 0x%02X at 0x%08X" % (funct, pc))
        return next_pc

    def execute_j(self, op, target, pc, next_pc):
        addr = ((pc + 4) & 0xF0000000) | (target << 2)
        if op == 0x03:
            self.regs[31] = next_pc
        return addr & MASK32

    def execute_branch(self, op, rs, rt, imm, pc, next_pc):
        s = self.regs[rs]
        t = self.regs[rt]
        taken = False
        if op == 0x04:
            taken = s == t
        elif op == 0x05:
            taken = s != t
        elif op == 0x06:
            taken = _s32(s) <= 0
        elif op == 0x07:
            taken = _s32(s) > 0
        if taken:
            return _u32(pc + 4 + (_sign_extend(imm, 16) << 2))
        return next_pc

    def execute_imm(self, op, rs, rt, imm, pc, next_pc):
        s = self.regs[rs]
        if op == 0x08:
            self._set(rt, _u32(s + _sign_extend(imm, 16)))
        elif op == 0x09:
            self._set(rt, _u32(s + _sign_extend(imm, 16)))
        elif op == 0x0A:
            self._set(rt, 1 if _s32(s) < _sign_extend(imm, 16) else 0)
        elif op == 0x0B:
            self._set(rt, 1 if s < _u32(_sign_extend(imm, 16)) else 0)
        elif op == 0x0C:
            self._set(rt, s & imm)
        elif op == 0x0D:
            self._set(rt, s | imm)
        elif op == 0x0E:
            self._set(rt, s ^ imm)
        elif op == 0x0F:
            self._set(rt, _u32(imm << 16))
        else:
            raise RuntimeError("unknown imm opcode 0x%02X" % op)
        return next_pc

    def execute_mem(self, op, rs, rt, imm, pc, next_pc):
        addr = _u32(self.regs[rs] + _sign_extend(imm, 16))
        if op == 0x20:
            self._set(rt, _u32(_sign_extend(self.read_byte(addr), 8)))
        elif op == 0x24:
            self._set(rt, self.read_byte(addr))
        elif op == 0x21:
            self._set(rt, _u32(_sign_extend(self.read_half(addr), 16)))
        elif op == 0x25:
            self._set(rt, self.read_half(addr))
        elif op == 0x23:
            self._set(rt, self.read_word(addr))
        elif op == 0x28:
            self.write_byte(addr, self.regs[rt])
        elif op == 0x29:
            self.write_half(addr, self.regs[rt])
        elif op == 0x2B:
            self.write_word(addr, self.regs[rt])
        else:
            raise RuntimeError("unknown mem opcode 0x%02X" % op)
        return next_pc

    def _set(self, reg, val):
        if reg != 0:
            self.regs[reg] = _u32(val)

    def result(self):
        files_out = {}
        for name, data in self.files.items():
            files_out[name] = bytes(data).hex()
        for fd, f in self.fds.items():
            if fd >= 3 and f["kind"] == "file":
                files_out[f["name"]] = bytes(f["data"]).hex()

        inspect_out = []
        for item in self.inspect:
            address = item["address"]
            length = item["length"]
            data = bytes(self.read_byte(address + i) for i in range(length))
            inspect_out.append({"address": address, "hex": data.hex()})

        return {
            "exit_code": self.exit_code,
            "registers": [self.regs[i] for i in range(32)],
            "hi": self.hi,
            "lo": self.lo,
            "steps": self.steps,
            "stdout_hex": bytes(self.stdout).hex(),
            "stderr_hex": bytes(self.stderr).hex(),
            "files": files_out,
            "inspect": inspect_out,
            "syscalls": self.syscalls,
        }


def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    machine = _Machine(payload, left, right)
    machine.run()
    return machine.result()
