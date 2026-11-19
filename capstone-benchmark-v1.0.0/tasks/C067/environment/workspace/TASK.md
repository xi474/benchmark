# C067 逐请求授权与临时凭据缓存

实现一个可独立导入和命令行运行的组件。核心接口`transform(payload)`返回下述JSON结果，不修改输入对象。`load_payload(input_path)`读取UTF8 JSON并返回对象；`build_component(input_path,output_path)`独立读取、计算并将结果写入UTF8 JSON，返回相同结果。三个入口都须在无旧产物的全新目录工作。

## 公开业务契约

输入ttl为正整数，clusters映射cluster到mode(local/remote)与services布尔可用表；policies映射user到允许规则列表，每条cluster/verb必须精确匹配，service可省略或为`*`以允许任一服务。events按非递减time排列，同刻按数组顺序。policy事件替换指定user的allow列表；service事件更新可用性；request事件给id/user/cluster/service/verb。

每个request必须重新授权，未允许则status=denied，不查服务/不签发凭据。允许后必须先查当前service，查不到则not_found，不签发也不从旧缓存绕过查找。local直接使用local凭据，不建缓存。remote每次解析reverse_tunnel路由；凭据缓存只保存以(user,cluster,service)为键的临时证书，不能保存授权结论或完整会话。到期条件expires<=now；清理发生在成功找到remote服务后的缓存访问。缓存miss按全局顺序签发cert-1、cert-2等，expires=now+ttl；hit不延期。

输出replies保持request顺序，拒绝仅有id/status；成功另有credential(local或cert-N)、route(local或reverse_tunnel)。计数authorizer_calls、service_lookups、remote_routes、certificates_issued及最终cache按user/cluster/service字典序排列，每项含键与credential/expires。

## 交付与公开检查

在`solution.py`实现三个入口；可自行新增业务文件。`python run_all.py --check`运行小型公开例。`python run_all.py --input public_input.json --output output.json`生成产物。运行不依赖作者目录、既有output、网络或隐藏服务；不得修改run_all.py、public_input.json和public_expected.json。验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。
