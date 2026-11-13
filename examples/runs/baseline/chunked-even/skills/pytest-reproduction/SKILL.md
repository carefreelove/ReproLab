---
name: pytest-reproduction
description: 将 Python 缺陷转为 pytest 测试。用于首次构造复现、fixture 与目标断言设计。
license: MIT
metadata:
  version: "1.0"
---

# pytest-reproduction

先阅读目标函数及调用方式，明确用户期望行为。
使用真实生产函数构造最小输入，先给出正向期望断言。
异常属于用户预期时使用 pytest.raises；故障现象中的异常应自然暴露。
生成测试前记录假设，运行后根据错误分类调整。
完成条件为测试实际采集并触发目标行为，随后提交独立验收。
可读取 assets/test_template.py 和 references/assertions.md。
