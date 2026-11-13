---
name: failure-triage
description: 在 pytest 收集、导入、运行环境、断言或超时失败后进行错误分类并调整调查路径。
license: MIT
metadata:
  version: "1.0"
---

# failure-triage

先通过 read_artifact 读取完整实验日志，区分运行器失败与目标行为。
导入错误先检查包名、源码位置和导入方式；收集错误先检查测试语法与命名。
目标断言失败或目标函数抛异常时回到用户契约，判断当前假设是否获得支持。
通过测试意味着该输入未复现，应调整输入或假设。
scripts/summarize.py 可归纳日志中的错误线索，输入应为已有日志文本。
记录 observed evidence 与 next_action，避免重复同一失败动作。
