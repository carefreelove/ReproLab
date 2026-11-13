# ReproLab 复现报告

source.money(amount) 接收十进制字符串，按 ROUND_HALF_UP 保留两位返回 Decimal。输入 2.675 的结果应为 Decimal("2.68")。

任务 `649f9c8f0622` · 状态 `completed` · 模式 `live`

仓库 `fixture/decimal-money` · 缺陷版本 `9b2fcdc3fee7270931948c087d1bf9965439a0d5`

验收修复版本 `2be85ebe8c93d4508d50f5b8e8facae8cdbfe030`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `82a1446c92208a33f80533d7ee7721218636cc19dc5ccc6787e2cfee426cd20f`

## 使用的 Skills

- `boundary-analysis` · 缺陷涉及十进制精度与 ROUND_HALF_UP 边界（2.675 二进制/浮点表示） · 内容 `9fdd5d488abcb74e2bbf0fcbe0ae89363135a7af187052c509d8c5a928a04e53`

## 计划与假设

```json
{
  "plan": [
    {
      "task": "定位 source.money 实现，确认舍入逻辑",
      "status": "done",
      "evidence": [
        "ar-2268de3dcc7acd95578e"
      ]
    },
    {
      "task": "激活 boundary-analysis 技能获取复现规范",
      "status": "done",
      "evidence": []
    },
    {
      "task": "编写针对 2.675 -> Decimal('2.68') 的复现测试",
      "status": "done",
      "evidence": []
    },
    {
      "task": "运行测试并依据真实错误更新假设",
      "status": "done",
      "evidence": [
        "ar-b7ba2f6dcd889b9a035a",
        "ar-61b7e41ce8a42bffd596"
      ]
    },
    {
      "task": "提交复现",
      "status": "in_progress",
      "evidence": []
    }
  ],
  "hypotheses": [
    {
      "id": "h1",
      "claim": "source.money 用 float(amount) 再 round(...,2)，2.675 的二进制浮点表示略小于 2.675，导致 round 得到 2.67，返回 Decimal('2.67') 而非契约要求的 Decimal('2.68')；对称地 -2.675 得到 -2.67。",
      "expected": "money('2.675') == Decimal('2.68') 断言失败，实际为 Decimal('2.67')",
      "status": "supported",
      "evidence": [
        "ar-b7ba2f6dcd889b9a035a",
        "ar-61b7e41ce8a42bffd596"
      ],
      "next_action": "假设已被真实断言失败支持（2.675 与 -2.675 均失败，正常值 1.234/1.236/0.00/1.235 通过），提交复现"
    }
  ]
}
```

## 实验

- `ex-b7275186ecdb` · 假设 `h1` · assertion_failure · 日志 `ar-b7ba2f6dcd889b9a035a`

## 调用统计

```json
{
  "model_calls": 9,
  "input_tokens": 46569,
  "output_tokens": 1767,
  "estimated_cost_cny": 0.128732,
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
