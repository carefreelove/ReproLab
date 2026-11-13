# ReproLab 复现报告

source.money(amount) 接收十进制字符串，按 ROUND_HALF_UP 保留两位返回 Decimal。输入 2.675 的结果应为 Decimal("2.68")。

任务 `98851c0cba1d` · 状态 `completed` · 模式 `live_baseline`

仓库 `fixture/decimal-money` · 缺陷版本 `9b2fcdc3fee7270931948c087d1bf9965439a0d5`

验收修复版本 `2be85ebe8c93d4508d50f5b8e8facae8cdbfe030`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `d9e8731bf436515b5401ba7af688bc1de26682d97f85473db26df7d811e8f7a3`

## 使用的 Skills


## 计划与假设

```json
{
  "plan": [],
  "hypotheses": []
}
```

## 实验


## 调用统计

```json
{
  "model_calls": 1,
  "input_tokens": 418,
  "output_tokens": 97,
  "estimated_cost_cny": 0.001935,
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
