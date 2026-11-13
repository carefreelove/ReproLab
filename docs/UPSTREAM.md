# 上游复用与项目开发

| 来源 | 实际用途 | ReproLab 的实现 |
| --- | --- | --- |
| mini-swe-agent 2.4.6 | DefaultAgent.step、query、serialize 及 Model/Environment 协议 | 新增复现任务生命周期、恢复、MCP 动作和独立验收 |
| MCP Python SDK 2.3.0 | Client、MCPServer、stdio、工具 schema | 新增任务工具、操作幂等、错误反馈和权限检查 |
| Agent Skills 规范 | SKILL.md 与渐进加载约定 | 新增四个 Skill、快照、覆盖规则、资源和脚本执行 |
| OpenAI SDK 3.50.0 | DeepSeek 兼容请求与 usage | 新增统一费用预留、结算、脱敏和上下文拼装 |
| pytest 9.2.0 | 测试运行与JUnit报告 | 新增结果分类、双版本稳定性与有效性检查 |
| SWE-bench | 失败转通过的评测方法参考 | 独立八题题集和单次生成对照 |
| more-itertools | 两条公开历史缺陷 | 固定版本快照、独立生成测试与验证记录 |

mini-swe-agent 参考 commit 为04d809ceab9df28f9adaed044884180159172930，MCP SDK 源码检查 commit 为77001c96f9507be0f4d009b83210a384a5e08bda。安装依赖以 uv.lock 中的包版本和哈希为准。

项目使用 AI 编程助手协作开发。任务规划、Skills、上下文、记忆和反思的应用层策略由本项目编写，执行结果以真实工具反馈和独立验收记录描述。上游 benchmark 指标归属于对应上游项目。

[mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) · [MCP SDK](https://github.com/modelcontextprotocol/python-sdk) · [Agent Skills](https://github.com/agentskills/agentskills) · [OpenAI SDK](https://github.com/openai/openai-python) · [pytest](https://github.com/pytest-dev/pytest) · [SWE-bench](https://github.com/SWE-bench/SWE-bench) · [more-itertools](https://github.com/more-itertools/more-itertools)
