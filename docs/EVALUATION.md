# 评测与实际运行记录

记录日期：2026-11-13。模型为 DeepSeek `deepseek-flash`，temperature=0，thinking disabled。宿主 Python 3.12，测试环境使用 Docker 中固定的 Python 3.12 / pytest 9.2.0。

## 题集和信息边界

六条自建缺陷覆盖空输入、时间窗口端点、共享状态、负参数、零容量与十进制舍入；两条真实历史缺陷来自 more-itertools。自建案例的版本 ID 是源码内容摘要，真实案例使用完整 Git commit SHA。

| 真实案例 | 缺陷版 | 修复版 | 来源 |
| --- | --- | --- | --- |
| chunked-even | `20c4ee5c63f8f8c35a37aee3b69d95cd2450c09a` | `08dca284ba5446a026afdc34067b658f9da989eb` | [PR #1342](https://github.com/more-itertools/more-itertools/pull/1342) |
| numeric-range | `08dca284ba5446a026afdc34067b658f9da989eb` | `f42daddf205f335fea6e200dad46049f33e71221` | [PR #1345](https://github.com/more-itertools/more-itertools/pull/1345) |

Agent 只读取缺陷版及用户问题，通过 MCP 编写和执行测试。修复版、修复 diff 与上游新增测试由独立验收器持有。公开运行包在任务结束后同时提供两版日志，供读者复查。固定夹具中的参考测试只用于脚本模型的协议检查，不提供给真实模型。

`verified` 要求同一测试哈希在缺陷版连续三次触发失败，在修复版连续三次通过，且静态检查无异常。静态规则检查固定失败、跳过、源码/版本断言及可确认的非法关键字调用；它们不能代替人工审查测试与需求的语义关系。

## 开发过程中的失败

[初轮原始记录](../examples/evaluation-initial.json)中，完整 Agent 为 **3/8 completed**，单次生成对照为 **6/8 completed**。失败包括：

- 模型把说明文字拼接在 artifact ID 后，反思状态更新未被接受，重复动作后停止。之后收紧 schema，并向模型返回具体字段错误。
- 对象 repr 的内存地址导致相同失败被误判为不稳定。之后仅归一化十六进制进程地址。
- 合法边界值 `sys.maxsize` 被过宽的静态规则拒绝。之后细化规则。
- numeric-range 测试使用不支持的 `step=` 关键字。之后增加基于缺陷版源码 AST 的保守调用签名检查。

[初轮空输入轨迹](../examples/runs/initial/empty-mean/report.md)与[初轮大数轨迹](../examples/runs/initial/numeric-range/report.md)保留失败。下表是修改实现后的第二轮运行，**不是盲测**，不将初轮和复跑混合计算成功率。

## 第二轮真实模型结果

完整 Agent 的八条记录最终均通过双版本验证；numeric-range 在原任务内恢复一次，累计调用仍计入原账本。每条单次对照恰好一次模型调用，只给原问题与最多 12 KB 相关源码，没有检索和执行反馈。两种方式的信息访问、调用和费用不同。

| 案例 | Agent / 对照 | 调用 | 实验 | 累计秒 | 估算费用 |
| --- | --- | --- | --- | --- | --- |
| [empty-mean](../examples/runs/full/empty-mean/report.md) | verified / verified | 9 | 1 | 15.41 | ¥0.120845 |
| [inclusive-window](../examples/runs/full/inclusive-window/report.md) | verified / verified | 9 | 1 | 17.92 | ¥0.137410 |
| [shared-state](../examples/runs/full/shared-state/report.md) | verified / verified | 9 | 1 | 15.98 | ¥0.125455 |
| [negative-offset](../examples/runs/full/negative-offset/report.md) | verified / verified | 9 | 1 | 15.51 | ¥0.121174 |
| [zero-capacity](../examples/runs/full/zero-capacity/report.md) | verified / verified | 9 | 1 | 15.48 | ¥0.127909 |
| [decimal-money](../examples/runs/full/decimal-money/report.md) | verified / verified | 9 | 1 | 15.74 | ¥0.128732 |
| [chunked-even](../examples/runs/full/chunked-even/report.md) | verified / verified | 9 | 1 | 18.59 | ¥0.195055 |
| [numeric-range](../examples/runs/full/numeric-range/report.md) | verified / verified | 21 | 2 | 43.87 | ¥0.586980 |

完整 Agent 84 次模型调用，估算费用 ¥1.543560；单次对照 8 次调用，¥0.035480。完整 Agent 任务累计耗时中位数约 15.86 秒；原始对照未记录完整任务墙钟时间，不能用于端到端耗时比较。逐次 API 耗时与验证耗时保存在事件中。最终镜像复核耗时与任务原始运行耗时分开记录，表中沿用原任务累计时间。

**这组结果没有显示完整 Agent 优于单次生成。** 六条自建缺陷很小，两条历史缺陷的问题描述也较明确。它主要验证工具协议、执行反馈、错误恢复与双版本验收能够实际连通，不能据此推断真实软件工程任务成功率。

## 消融

| 配置 | shared-state | chunked-even | 模型调用 | 估算费用 |
| --- | --- | --- | --- | --- |
| 完整 Agent | verified | verified | 18 | ¥0.320510 |
| 关闭 Skills | verified | verified | 16 | ¥0.239656 |
| 关闭显式反思状态反馈 | verified | verified | 18 | ¥0.316114 |

[消融原始记录](../examples/ablation-live.json)。关闭 Skills 时不暴露目录，激活工具拒绝请求。关闭显式反思时移除假设状态上下文和强制更新 gate，并调整相关提示；模型自身仍可以根据工具结果推理。每种配置及案例采用独立记忆 namespace。

每个配置只有两个案例、一次运行，未观察到成功率差异。调用量与费用差异仅描述本次运行，不作因果归因。

## 两种恢复示例

### 自然发现的无效测试

[numeric-range 运行包](../examples/runs/full/numeric-range/report.json)记录首次验收不通过、原测试哈希及修改 diff。初稿在一个大数比较失败之前使用了非法关键字调用；独立验收阻止了过早成功。恢复时只提供缺陷版源码签名检查结果，Agent 查找构造函数、改用位置参数、重跑并更新假设，最终完成三次缺陷版失败和三次修复版通过。修复版原始资料无法通过 Agent 的 `read_artifact` 或上下文索引读取。

### 明确标记的受控演示

[导入错误恢复](../examples/runs/controlled-import-recovery/report.json)由宿主预先注入 `from source import average`，这一步属于人为设置。随后真实 Agent 激活 `failure-triage`，调用 `scripts/summarize.py`，定位正确函数，覆盖测试并提交独立验收。共 9 次付费调用、两次实验（一次为宿主预置），估算 ¥0.137130。

该示例证明 Skill 脚本、日志取回及测试调整的实际调用路径，不计入八题结果。可用 `uv run python examples/demo_recovery.py` 再次运行，会产生 API 费用。

## 费用账本

所有开发探测、失败、复跑、对照、消融与演示合计 **263 次模型调用，¥4.665886**，未确认用量 **0**，低于独立 ¥20 上限。[逐任务账本摘要](../examples/cost-summary.json)保留全部记录。费用按官方高峰未命中缓存费率、固定 8 CNY/USD 保守估算，实际账单可能更低。

## 自动检查与复现

- 55 项测试覆盖输入与路径、Skills 快照、MCP stdio、上下文裁剪、费用预留、任务恢复、产物哈希、测试分类、双版本验收及真实 Docker 约束。
- 八条 `offline_synthetic` 协议回放通过。其测试由固定夹具提供，模型调用为零，单独保存于[离线记录](../examples/evaluation-offline.json)。
- Ruff 检查和格式检查通过。CI 在 Linux 上重新安装依赖、构建镜像，运行单元测试、Docker 测试及八条协议回放。

从仓库根目录重新运行公开测试，不需要模型凭据：

```bash
uv sync --frozen
docker build -t reprolab-python:0.1.0 -f docker/Dockerfile .
uv run reprolab replay examples/runs/full/numeric-range
```

`replay` 检查测试哈希和固定版本，新建任务并重新执行独立验收。真实案例首次需要联网下载源码；测试容器运行阶段关闭网络。验证缓存绑定测试哈希、镜像内容 ID、版本与重复次数，镜像改变时重新执行。

## 已知限制和下一步

- 支持受控、依赖明确的纯 Python 项目。Docker 是资源与权限约束，不提供针对恶意内核攻击的强隔离。
- 尚未覆盖复杂安装、异步/并发、跨进程服务和长耗时缺陷；公开仓库快照遇到链接会拒绝读取。
- 自建案例规模小，两个真实案例可能在模型训练数据中出现；没有排除记忆效应。
- 当前经验卡片严格限定同仓库同版本，尚无跨版本经验迁移的质量评测。
- 下一步优先增加不完整描述的真实案例和重复种子运行，盲测无效测试识别率、超时恢复及上下文裁剪，再讨论引入更复杂的检索或多 Agent。
