# C031 真实交互Bash终端与控制键

实现一个可独立导入和命令行运行的组件。核心接口`transform(payload)`返回下述JSON结果，不修改输入对象。`load_payload(input_path)`读取UTF8 JSON并返回对象；`build_component(input_path,output_path)`独立读取、计算并将结果写入UTF8 JSON，返回相同结果。三个入口都须在无旧产物的全新目录工作。

## 公开业务契约

Linux环境中使用真实PTY启动交互/bin/bash；每次transform是新临时目录与独立进程会话，HOME指向该目录，预先创建空.hushlogin屏蔽系统登录提示，TERM=dumb、LC_ALL=C、HISTFILE=/dev/null。bash以--noprofile --rcfile <临时文件> -i启动。rc内容依次为PS1='PROMPT> '、PS2='CONT> '、HISTFILE=/dev/null，再追加输入startup字符串(默认空)。这样startup必须被交互shell实际加载。

输入steps，每步keys为字符串列表；Enter映射CR、C-c映射0x03、C-d映射0x04、C-u映射0x15、Tab映射0x09、Backspace映射0x7f；其他字符串按UTF8原样发送。将该步所有keys串接后一次写入PTY。until为待观测标记，null代表等到PTY EOF。初始先读到PROMPT>；每步读到until，保留标记及同一输出突发已经到达的剩余字节。每次等待timeout_seconds默认4秒，是正常本地进程响应预算。

输出chunks为初始读取与每步读取的完整终端文本，包括终端回显；仅规范化CRLF/CR为LF/删除孤立CR，不移除回显、控制键显示或shell提示符。closed表示是否已经读到EOF。单个transform结束必须清理所属进程组及PTY。Ctrl-C应作用于当前前台程序，不能破坏之后的shell；Ctrl-D在read中与shell空闲的语义不同。输入命令仅在临时目录内运行，无网络、提权或真实用户数据访问。不能用静态规则模拟命令输出。

## 交付与公开检查

在`solution.py`实现三个入口；可自行新增业务文件。`python run_all.py --check`运行小型公开例。`python run_all.py --input public_input.json --output output.json`生成产物。运行不依赖作者目录、既有output、网络或隐藏服务；不得修改run_all.py、public_input.json和public_expected.json。验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。
