# C062 多后端快照轮询的关闭屏障

实现一个可独立导入和命令行运行的组件。核心接口`transform(payload)`返回下述JSON结果，不修改输入对象。`load_payload(input_path)`读取UTF8 JSON并返回对象；`build_component(input_path,output_path)`独立读取、计算并将结果写入UTF8 JSON，返回相同结果。三个入口都须在无旧产物的全新目录工作。

## 公开业务契约

输入`events`按非递减整数time排列，同刻按数组顺序。事件有store与op：open(backend为git/local/s3/azure/oci之一，可给revision，默认0)、poll(job)、complete(job,changed，若changed则含revision)、close。每store只open一次，job唯一，complete与在途job一致；所有开始的job最终均有complete。后端名字不改变生命周期语义。

每store最多一个在途更新。open状态第一次poll启动job，再次poll合并而不替换；closing/closed状态拒绝poll。close无在途job立即返回并关闭；有在途job则发取消，直到对应callback结束才返回。取消后的complete不得发布快照。对closing再次close等待同一屏障；closed再次close立即返回。未取消complete的changed=true发布revision并令updates加1；false保持原快照。

输出events审计：opened、poll_started(job)、poll_coalesced、poll_rejected、cancel_sent(job)、close_waiting、callback_cancelled(job)、snapshot_updated(job)、poll_unchanged(job)、close_returned。字段均含time/store，按照事件处理顺序；一次取消complete先callback_cancelled再close_returned。stores保留backend/state/job/revision/closed_at/updates。close返回后不再改变该store快照。

## 交付与公开检查

在`solution.py`实现三个入口；可自行新增业务文件。`python run_all.py --check`运行小型公开例。`python run_all.py --input public_input.json --output output.json`生成产物。运行不依赖作者目录、既有output、网络或隐藏服务；不得修改run_all.py、public_input.json和public_expected.json。验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。
