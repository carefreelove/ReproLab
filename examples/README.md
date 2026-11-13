# 可复查的运行包

所有 `live` / `live_baseline` 记录来自真实 DeepSeek 请求。`offline_synthetic` 使用预设动作和测试，只验证执行协议。记录说明见[评测文档](../docs/EVALUATION.md)。

| 目录 / 文件 | 内容 |
| --- | --- |
| [runs/full](runs/full/) | 修改实现后八条完整 Agent 记录 |
| [runs/baseline](runs/baseline/) | 同模型一次生成对照，未提供工具反馈 |
| [runs/initial](runs/initial/) | 初轮失败的两份完整轨迹 |
| [runs/no_skills](runs/no_skills/) | 两条关闭 Skills 的真实模型记录 |
| [runs/no_explicit_reflection](runs/no_explicit_reflection/) | 两条关闭显式反思反馈的记录 |
| [runs/controlled-import-recovery](runs/controlled-import-recovery/) | 人为预置导入错误，之后由真实 Agent 修正 |
| [evaluation-initial.json](evaluation-initial.json) | 完整初轮结果，包含失败 |
| [evaluation-live.json](evaluation-live.json) | 最终复核后的第二轮和对照结果 |
| [ablation-live.json](ablation-live.json) | 消融结果 |
| [evaluation-offline.json](evaluation-offline.json) | 脚本模型的协议验证 |
| [cost-summary.json](cost-summary.json) | 所有付费调用的逐任务保守估算 |

运行包包含 `report.md`、`report.json`、事件与模型轨迹、生成测试、实际日志及 Skill 快照。历史快照保持当时内容，与当前内置 Skill 的元数据可能不同。运行后公开的修复版日志供用户核对，执行时不会暴露给 Agent。

无需 API 费用即可重新验收已有测试：

```bash
uv run reprolab replay examples/runs/full/chunked-even
```

需要已构建的 Docker 镜像，首次下载历史源码需要联网。此命令重新执行已有测试，不重新生成 Agent 调查轨迹。
