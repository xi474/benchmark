# market_ranking

输入字段为 market, top。缺省字段沿用原题约定。

按最新市场日的 30 天窗口、相对绝对涨跌幅和代号打破平局，返回前 top 个房间代号（保持排名）。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check market_ranking
python -B component_runtime.py run market_ranking
```
