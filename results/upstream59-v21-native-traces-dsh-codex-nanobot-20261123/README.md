# Upstream59 v2.1.0 · DSH、Codex、Nanobot 运行轨迹

DeepSeek V4 Pro 普通模式，三套 Harness 各 59 题，共 177 个矩阵选定题位。
每套包含 30 个 v2.1 实跑题、25 个沿用历史轨迹后离线复评分的 MP 题、4 个沿用 v2.0 的 N 题。
没有为导出新跑试次。ZIP 解压后可直接读取 JSONL、JSON 和观测 CSV。

每包含原生会话或运行事件、保存下来的请求观察快照、工具和资源遥测，以及本题独立筛选的网关事件。
DSH 会话由 Zstandard 解压为 JSONL，Codex 保留 native rollout 和 trajectory，Nanobot 保留两版运行事件。
源文件没有记录的事件仍记为缺失。网关每题映射已按本题隔离，批次总量字段仍代表原来观察到的批次状态。

发布副本只脱敏凭据、长不透明载荷和本机路径。保留事件顺序和异常终态。
候选目录、隐藏评分器、环境配置、原始凭据和其他题位不随包发布。
每包的 `case.json` 记录原运行身份、评分标签、各文件的源与导出 SHA-256，以及 JSONL 行数。

[机器可读目录与 ZIP 校验值](manifest.json)

## 按题下载

- `C007` [dsh](dsh/C007.zip) · [codex](codex/C007.zip) · [nanobot](nanobot/C007.zip)
- `C008` [dsh](dsh/C008.zip) · [codex](codex/C008.zip) · [nanobot](nanobot/C008.zip)
- `C009` [dsh](dsh/C009.zip) · [codex](codex/C009.zip) · [nanobot](nanobot/C009.zip)
- `C011` [dsh](dsh/C011.zip) · [codex](codex/C011.zip) · [nanobot](nanobot/C011.zip)
- `C017` [dsh](dsh/C017.zip) · [codex](codex/C017.zip) · [nanobot](nanobot/C017.zip)
- `C031` [dsh](dsh/C031.zip) · [codex](codex/C031.zip) · [nanobot](nanobot/C031.zip)
- `C033` [dsh](dsh/C033.zip) · [codex](codex/C033.zip) · [nanobot](nanobot/C033.zip)
- `C039` [dsh](dsh/C039.zip) · [codex](codex/C039.zip) · [nanobot](nanobot/C039.zip)
- `C049` [dsh](dsh/C049.zip) · [codex](codex/C049.zip) · [nanobot](nanobot/C049.zip)
- `C055` [dsh](dsh/C055.zip) · [codex](codex/C055.zip) · [nanobot](nanobot/C055.zip)
- `C056` [dsh](dsh/C056.zip) · [codex](codex/C056.zip) · [nanobot](nanobot/C056.zip)
- `C058` [dsh](dsh/C058.zip) · [codex](codex/C058.zip) · [nanobot](nanobot/C058.zip)
- `C062` [dsh](dsh/C062.zip) · [codex](codex/C062.zip) · [nanobot](nanobot/C062.zip)
- `C066` [dsh](dsh/C066.zip) · [codex](codex/C066.zip) · [nanobot](nanobot/C066.zip)
- `C067` [dsh](dsh/C067.zip) · [codex](codex/C067.zip) · [nanobot](nanobot/C067.zip)
- `C068` [dsh](dsh/C068.zip) · [codex](codex/C068.zip) · [nanobot](nanobot/C068.zip)
- `C069` [dsh](dsh/C069.zip) · [codex](codex/C069.zip) · [nanobot](nanobot/C069.zip)
- `C074` [dsh](dsh/C074.zip) · [codex](codex/C074.zip) · [nanobot](nanobot/C074.zip)
- `C077` [dsh](dsh/C077.zip) · [codex](codex/C077.zip) · [nanobot](nanobot/C077.zip)
- `C079` [dsh](dsh/C079.zip) · [codex](codex/C079.zip) · [nanobot](nanobot/C079.zip)
- `MP01` [dsh](dsh/MP01.zip) · [codex](codex/MP01.zip) · [nanobot](nanobot/MP01.zip)
- `MP02` [dsh](dsh/MP02.zip) · [codex](codex/MP02.zip) · [nanobot](nanobot/MP02.zip)
- `MP03` [dsh](dsh/MP03.zip) · [codex](codex/MP03.zip) · [nanobot](nanobot/MP03.zip)
- `MP04` [dsh](dsh/MP04.zip) · [codex](codex/MP04.zip) · [nanobot](nanobot/MP04.zip)
- `MP05` [dsh](dsh/MP05.zip) · [codex](codex/MP05.zip) · [nanobot](nanobot/MP05.zip)
- `MP06` [dsh](dsh/MP06.zip) · [codex](codex/MP06.zip) · [nanobot](nanobot/MP06.zip)
- `MP07` [dsh](dsh/MP07.zip) · [codex](codex/MP07.zip) · [nanobot](nanobot/MP07.zip)
- `MP08` [dsh](dsh/MP08.zip) · [codex](codex/MP08.zip) · [nanobot](nanobot/MP08.zip)
- `MP09` [dsh](dsh/MP09.zip) · [codex](codex/MP09.zip) · [nanobot](nanobot/MP09.zip)
- `MP10` [dsh](dsh/MP10.zip) · [codex](codex/MP10.zip) · [nanobot](nanobot/MP10.zip)
- `MP12` [dsh](dsh/MP12.zip) · [codex](codex/MP12.zip) · [nanobot](nanobot/MP12.zip)
- `MP13` [dsh](dsh/MP13.zip) · [codex](codex/MP13.zip) · [nanobot](nanobot/MP13.zip)
- `MP14` [dsh](dsh/MP14.zip) · [codex](codex/MP14.zip) · [nanobot](nanobot/MP14.zip)
- `MP15` [dsh](dsh/MP15.zip) · [codex](codex/MP15.zip) · [nanobot](nanobot/MP15.zip)
- `MP16` [dsh](dsh/MP16.zip) · [codex](codex/MP16.zip) · [nanobot](nanobot/MP16.zip)
- `MP17` [dsh](dsh/MP17.zip) · [codex](codex/MP17.zip) · [nanobot](nanobot/MP17.zip)
- `MP18` [dsh](dsh/MP18.zip) · [codex](codex/MP18.zip) · [nanobot](nanobot/MP18.zip)
- `MP19` [dsh](dsh/MP19.zip) · [codex](codex/MP19.zip) · [nanobot](nanobot/MP19.zip)
- `MP20` [dsh](dsh/MP20.zip) · [codex](codex/MP20.zip) · [nanobot](nanobot/MP20.zip)
- `MP21` [dsh](dsh/MP21.zip) · [codex](codex/MP21.zip) · [nanobot](nanobot/MP21.zip)
- `MP22` [dsh](dsh/MP22.zip) · [codex](codex/MP22.zip) · [nanobot](nanobot/MP22.zip)
- `MP23` [dsh](dsh/MP23.zip) · [codex](codex/MP23.zip) · [nanobot](nanobot/MP23.zip)
- `MP24` [dsh](dsh/MP24.zip) · [codex](codex/MP24.zip) · [nanobot](nanobot/MP24.zip)
- `MP25` [dsh](dsh/MP25.zip) · [codex](codex/MP25.zip) · [nanobot](nanobot/MP25.zip)
- `MP26` [dsh](dsh/MP26.zip) · [codex](codex/MP26.zip) · [nanobot](nanobot/MP26.zip)
- `MS02` [dsh](dsh/MS02.zip) · [codex](codex/MS02.zip) · [nanobot](nanobot/MS02.zip)
- `MS11` [dsh](dsh/MS11.zip) · [codex](codex/MS11.zip) · [nanobot](nanobot/MS11.zip)
- `MS12` [dsh](dsh/MS12.zip) · [codex](codex/MS12.zip) · [nanobot](nanobot/MS12.zip)
- `MS14` [dsh](dsh/MS14.zip) · [codex](codex/MS14.zip) · [nanobot](nanobot/MS14.zip)
- `MS23` [dsh](dsh/MS23.zip) · [codex](codex/MS23.zip) · [nanobot](nanobot/MS23.zip)
- `MS28` [dsh](dsh/MS28.zip) · [codex](codex/MS28.zip) · [nanobot](nanobot/MS28.zip)
- `MS29` [dsh](dsh/MS29.zip) · [codex](codex/MS29.zip) · [nanobot](nanobot/MS29.zip)
- `MS30` [dsh](dsh/MS30.zip) · [codex](codex/MS30.zip) · [nanobot](nanobot/MS30.zip)
- `MS41` [dsh](dsh/MS41.zip) · [codex](codex/MS41.zip) · [nanobot](nanobot/MS41.zip)
- `MS42` [dsh](dsh/MS42.zip) · [codex](codex/MS42.zip) · [nanobot](nanobot/MS42.zip)
- `N11` [dsh](dsh/N11.zip) · [codex](codex/N11.zip) · [nanobot](nanobot/N11.zip)
- `N17` [dsh](dsh/N17.zip) · [codex](codex/N17.zip) · [nanobot](nanobot/N17.zip)
- `N22` [dsh](dsh/N22.zip) · [codex](codex/N22.zip) · [nanobot](nanobot/N22.zip)
- `N24` [dsh](dsh/N24.zip) · [codex](codex/N24.zip) · [nanobot](nanobot/N24.zip)
