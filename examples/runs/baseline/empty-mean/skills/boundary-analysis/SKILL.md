---
name: boundary-analysis
description: 调查空输入、零、负数、大数、时间端点与十进制精度问题，构造边界参数化测试。
license: MIT
metadata:
  version: "1.0"
---

# boundary-analysis

读取函数契约及与边界相关的分支。
选择正常值、临界值与相邻值，分别描述预期行为。
scripts/boundaries.py 可生成整数边界样本。
用 pytest.mark.parametrize 覆盖有意义的值。大数范围采用比较或哈希，避免展开超长序列。
复现失败后对照实际异常与假设，不扩大为无关随机测试。
完成条件为定位到至少一个契约不满足的边界，并保留正常值校验。
