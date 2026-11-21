# mobile_cable

输入字段为 records。缺省字段沿用原题约定。

标准化 ('mobile', 'cable') 渠道记录，返回 [原位置,字段对象] 数组。对象字段 id,first,last,dob,ssn,mail,phone,address，日期 ISO，文字小写去非字母数字，电话及证件仅留数字。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check mobile_cable
python -B component_runtime.py run mobile_cable
```
