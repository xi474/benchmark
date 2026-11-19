# C033 ELF装载与MIPS32延迟槽/文件IO

实现一个可独立导入和命令行运行的组件。核心接口`transform(payload)`返回下述JSON结果，不修改输入对象。`load_payload(input_path)`读取UTF8 JSON并返回对象；`build_component(input_path,output_path)`独立读取、计算并将结果写入UTF8 JSON，返回相同结果。三个入口都须在无旧产物的全新目录工作。

## 公开业务契约

输入elf_hex为合法ELF32 little-endian ET_EXEC、EM_MIPS程序；按PT_LOAD的p_offset/p_vaddr/p_filesz/p_memsz装载，BSS补零。entry来自ELF头，内存为32位地址字节寻址。files映射UTF8文件名到初始字节hex；stdin_hex可省略；inspect为{address,length}列表。初始通用寄存器0，sp(29)默认0x7fff0000或stack_pointer，hi/lo为0。所有地址/无符号值为0..2^32-1，算术按32位回绕，r0始终为0。

公开指令子集：sll/srl/sra，jr/jalr，add/addu/sub/subu，and/or/xor/nor，slt/sltu，mfhi/mflo/mthi/mtlo，mult/multu/div/divu，syscall，j/jal，beq/bne/blez/bgtz，addi/addiu/slti/sltiu/andi/ori/xori/lui，lb/lbu/lh/lhu/lw/sb/sh/sw。有符号比较/算术右移用二补码；字节/半字加载按指令符号扩展；内存小端；立即数除andi/ori/xori/lui外符号扩展。合法输入无有符号溢出陷阱、除0、未对齐访问或延迟槽中的另一跳转。

所有跳转/分支有一个延迟槽；taken分支目标PC+4+(signext(imm)<<2)，j/jal使用PC+4高4位和26位目标；jal/jalr写回PC+8。div向0截断，hi为余数；mult hi/lo为64位乘积高低32位。

syscall编号在v0(2)，参数a0/a1/a2(4/5/6)，结果v0，成功a3(7)=0：4001 exit(a0低8位)；4003 read(fd,buffer,n)；4004 write(fd,buffer,n)；4005 open(filename,flags,mode)，flags=0只读已有文件、1创建/截断、9追加创建；4006 close(fd)。fd0为stdin，1/2为stdout/stderr，open从3起单调分配，文件偏移各fd独立；输入均为合法操作，无未知syscall。程序在max_steps(默认20000)内exit。

输出exit_code、registers(32个无符号值)、hi、lo、steps(含exit指令)、stdout_hex、stderr_hex、所有最终files、inspect每段address/hex、syscalls按调用顺序含number及调用前args=[a0,a1,a2]。这是公开子集解释器改编，不要求启动原DOOM或实现全部MIPS/FPU。

## 交付与公开检查

在`solution.py`实现三个入口；可自行新增业务文件。`python run_all.py --check`运行小型公开例。`python run_all.py --input public_input.json --output output.json`生成产物。运行不依赖作者目录、既有output、网络或隐藏服务；不得修改run_all.py、public_input.json和public_expected.json。验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。
