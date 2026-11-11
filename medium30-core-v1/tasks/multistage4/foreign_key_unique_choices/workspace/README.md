# N12 关联条件下不重复的外键选项

按关联记录筛选外键候选，产生一份身份唯一、条件正确的表单选项。

## 本版输入与业务范围

用小型人物/关联表和有限谓词 DSL 替代 ORM；保留存在性语义与目标身份，输出选项和匹配解释。

- `stages/base_candidates`：entities=[{id:整数,name,active:bool}]。返回active=true的实体列表，保持输入顺序，不按name合并实体。
- `stages/related_matches`：relations=[{entity:ID,funny:bool,weight:整数}]。返回每条 funny=true且weight>=minimum的关联记录的entity ID，保留关系顺序及重复值。条件必须在同一关联行成立。
- `stages/form_choices`：按实体身份做半连接，返回 [{id,label:name}]。每个候选最多一次，保持候选原顺序；同名不同ID仍为不同选项。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
