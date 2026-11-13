---
name: iterator-state
description: 调查迭代器消耗、生成器延迟执行及实例间可变状态共享。
license: MIT
metadata:
  version: "1.0"
---

# iterator-state

对迭代器调用前后分别观察剩余内容。
需要执行生成器才能触发函数体，使用 list() 或 next() 明确推进。
无效参数应按用户描述检查是否消耗源数据，保存外部迭代器引用。
实例共享状态通过创建两个独立实例、只修改一个再观察另一个来检验。
assets/tracing_iterator.py 提供消耗追踪类，可复制到生成测试。
完成条件为同时展示调用结果与相关状态变化。
