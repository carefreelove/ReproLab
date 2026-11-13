# ReproLab 复现报告

source.mean([]) 应返回 0，非空输入返回算术平均值。当前空列表会失败，请生成测试。

任务 `e75c14b1a885` · 状态 `completed` · 模式 `live`

仓库 `fixture/empty-mean` · 缺陷版本 `0bb06820d5dbd4aeeba094a435744772a2a76f51`

验收修复版本 `50a825ee574abf95dd1ba5bb3a70bbb55a7fd307`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `5d057516966b02d5cd66d24303a032dc8e502c2b154b06b9d3490010f5c01c79`

## 使用的 Skills

- `boundary-analysis` · 缺陷涉及空列表边界输入，需要边界参数化测试策略 · 内容 `9fdd5d488abcb74e2bbf0fcbe0ae89363135a7af187052c509d8c5a928a04e53`

## 计划与假设

```json
{
  "plan": [
    {
      "task": "定位 source.mean 实现与空列表处理逻辑",
      "status": "done",
      "evidence": [
        "ar-32de8499db8aaf3b757f"
      ]
    },
    {
      "task": "激活 boundary-analysis 技能获取复现规范",
      "status": "done",
      "evidence": []
    },
    {
      "task": "记录假设并编写 pytest 复现测试（空列表返回0，非空返回均值）",
      "status": "done",
      "evidence": [
        "ar-c9c426a9dca79826e84e"
      ]
    },
    {
      "task": "运行测试确认目标行为被触发并提交复现",
      "status": "in_progress",
      "evidence": [
        "ar-c9c426a9dca79826e84e",
        "ar-26bbb75205572622e945"
      ]
    }
  ],
  "hypotheses": [
    {
      "id": "h1-empty-mean",
      "claim": "source.mean 直接执行 sum(values)/len(values)，空列表时 len 为 0 触发 ZeroDivisionError，而契约要求返回 0；非空输入应返回算术平均值。",
      "expected": "mean([]) 返回 0（当前实现抛 ZeroDivisionError）；非空参数化用例全部通过。",
      "status": "supported",
      "evidence": [
        "ar-c9c426a9dca79826e84e",
        "ar-26bbb75205572622e945"
      ],
      "next_action": "目标行为已触发（空列表 ZeroDivisionError，6 个非空用例通过），提交复现。"
    }
  ]
}
```

## 实验

- `ex-3e57841db53f` · 假设 `h1-empty-mean` · assertion_failure · 日志 `ar-c9c426a9dca79826e84e`

## 调用统计

```json
{
  "model_calls": 9,
  "input_tokens": 44163,
  "output_tokens": 1547,
  "estimated_cost_cny": 0.120845,
  "global_accounted_cny": 4.665886,
  "global_unconfirmed_calls": 0,
  "price_date": "2026-11-13",
  "input_cny_per_million": 2.4,
  "output_cny_per_million": 9.6,
  "usd_conversion": 8
}
```

## 验证边界

- 双版本差异及静态规则提供复现依据，测试语义仍需结合原始问题审查。
- 普通容器提供受约束执行，适用范围为受控的纯 Python 项目。
