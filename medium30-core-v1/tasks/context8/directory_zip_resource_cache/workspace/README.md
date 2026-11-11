# N20 目录与 ZIP 包的资源预加载

从普通目录或 ZIP 包中发现指定 HTML/JS 资源，构建同一缓存，并在预加载后通过缓存返回内容。

## 本版输入与业务范围

仅保留源题列明的目录和扩展名、POSIX 相对路径、两种载体及缓存命中语义；不运行浏览器。

- `packages/directory_resources`：files={POSIX相对路径:UTF8内容}，patterns=[{directory,extension}]。在目录载体中发现每个目录直接子文件，后缀匹配，返回排序唯一路径；不递归其他目录。只用受控临时目录，输入路径合法。
- `packages/zip_resources`：与directory_resources相同，但载体为zipfile.Path，不依赖其未提供的glob方法。
- `packages/preloaded_cache`：两载体路径集合一致时，返回 {路径:内容} 的预加载缓存，不纳入不匹配文件。
- `packages/offline_reads`：仅根据缓存按requests顺序返回 {paths:排序缓存键,values:请求内容列表}。原载体不作为本接口输入；在无源文件新目录也能构建。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
