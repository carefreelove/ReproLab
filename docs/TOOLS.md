# MCP、Skills 与状态接口

## 通信

CLI 中的 MCPEnvironment 创建官方 Client，启动绑定 run-id 的 stdio Server。连接后记录协议版本，并通过 list_tools 获取工具定义。模型产生工具调用，Environment 转为 MCP call_tool，请求 meta 中的 reprolab/operation 保存稳定 tool-call ID。

Server 结果通常包含 ok 与 data，领域拒绝返回 ok=false 和 error.code/message。协议 schema 错误使用 MCP 的 is_error，并将脱敏后的字段与约束反馈给模型。每个操作记录参数、产物引用和耗时。

## 工具

| 工具 | 主要输入 | 返回 |
| --- | --- | --- |
| update_plan | items，最多8项 | 任务、状态、证据引用 |
| record_hypothesis | hypothesis | claim、expected、status、evidence、next_action |
| lookup_experience | 无 | 同仓库、commit、namespace 的已验证经验 |
| activate_skill | name、reason | 内容哈希、正文和资源目录 |
| read_skill_resource | name、path | 已激活 Skill 的资源内容 |
| run_skill_script | name、path、arguments | 容器脚本输出与 artifact |
| list_files | path、pattern、offset | 至多80条目录项及下一页 |
| search_code | query、path | 至多20条字面关键词命中 |
| read_file | path、start_line、end_line | 至多200行、16 KB，带原始行号 |
| write_reproducer | path、content | 测试哈希及静态检查问题 |
| run_tests | 无 | 实验ID、假设、结果类别、日志与JUnit artifact |
| read_artifact | artifact_id、start_line | 原始资料片段与截断标记 |
| submit_reproducer | summary | 冻结的测试哈希和实验引用 |

生成测试限定为 test_*.py，每个文件至多24 KB。evidence 字段填写 ar- 加20位十六进制的原始 ID。写入和实验阶段受假设、反思、任务状态及数量限制。

## Skill 生命周期

SKILL.md 使用 YAML name、description 与 Markdown 正文，目录名须与 name 一致。资源限制单文件32 KB、总计128 KB，拒绝链接与越界路径。启动时只向模型提供名称和描述。

显式 skills-dir 覆盖同名内置 Skill。整个选中目录在任务创建时复制并计算文件哈希。激活和资源读取校验快照一致性。重复激活复用同一份活动状态，并保留加载事件。

Skill 脚本限定 scripts/*.py，JSON 输入至多16 KB，在受限容器中运行，输出转为 artifact。其声明用于描述能力需求，实际执行权限由工具控制。

## 数据与恢复

report.json 的 schema_version 为1.0。报告包含问题、源码版本、计划、假设、Skills、实验、提交、独立验收、产物索引和费用统计。trajectory.json 沿用 mini-swe-agent-1.1 的轨迹结构，并使用 ReproLab 的 Model 与 Environment 配置说明。

已完成的独立验收绑定测试哈希和验证算法版本。任务 resume 恢复消息、调用数、操作结果和累计时限。公开运行包可以通过 reprolab replay <bundle-directory> 下载固定源码并重新验收，过程使用已生成测试。
