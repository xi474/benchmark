# C069 会话续期、角色资源与身份编码

实现一个可独立导入和命令行运行的组件。核心接口`transform(payload)`返回下述JSON结果，不修改输入对象。`load_payload(input_path)`读取UTF8 JSON并返回对象；`build_component(input_path,output_path)`独立读取、计算并将结果写入UTF8 JSON，返回相同结果。三个入口都须在无旧产物的全新目录工作。

## 公开业务契约

输入user{name,roles,traits}、start_time、session_ttl、access_requests映射和events。traits固定含logins/db_users字符串列表。初始session为s0(可用initial_id覆盖)，登录时间start_time、expiry=start_time+ttl，缓存当时user。每个已批准request有approved/expiry与可选roles/resources。events按time递增，同刻按数组顺序。

update_user只替换给出的roles/traits。renew给唯一id、prev与可选reload_user、switchback、access_request。prev必须是已成功创建会话。prev.expiry<=now则expired。默认延用prev缓存user；reload_user使用最新后端user。switchback清空所有临时request与资源。assume新request须approved且未过期，否则request_unavailable；同一会话链已存在资源request时再assume任一资源request均resource_already_active。角色request可累积并去重。没有显式切回时，活跃request不得静默丢弃，到期则request_unavailable。

成功session的角色是缓存user基础角色与活跃request角色的并集，resources为活跃request资源并集，均排序。expiry=min(now+ttl, 所有活跃request.expiry)，无request则now+ttl；最初login_time不变。编码SSH-MODEL1为roles/allowed_resources/extensions/login_time/expires对象；TLS-MODEL1为user/active_requests/login_time/expires对象，active_requests排序。对象JSON采用ensure_ascii=false、sort_keys=true、separators=(',',':')，UTF8后base64url去掉末尾`=`，加`SSH-MODEL1.`或`TLS-MODEL1.`前缀。这是公开身份载体模型，不是实际SSH/TLS签名证书。

输出replies按renew顺序；失败含id/status；成功含id/status=ok/ssh_certificate/tls_certificate。session_ids按创建顺序含s0及所有成功id。失败不创建会话也不修改prev。输入不会同时switchback并assume，也不要求处理未承诺的坏编码。

## 交付与公开检查

在`solution.py`实现三个入口；可自行新增业务文件。`python run_all.py --check`运行小型公开例。`python run_all.py --input public_input.json --output output.json`生成产物。运行不依赖作者目录、既有output、网络或隐藏服务；不得修改run_all.py、public_input.json和public_expected.json。验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/user_history/work.py` | 记录各续期事件发生时的用户快照，重放 update_user 的 roles、traits；以原位置字符串为键。 | `components/user_history/result.json` |
| `components/grant_catalog/work.py` | 生成授权条目的有效条件和有序角色/资源集合。以原授权 ID 为键，每项含 approved、expiry、roles、resources。 | `components/grant_catalog/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check user_history
python -B component_runtime.py run user_history
python -B component_runtime.py check grant_catalog
python -B component_runtime.py run grant_catalog
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
