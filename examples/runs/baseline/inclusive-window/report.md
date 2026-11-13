# ReproLab 复现报告

source.in_window(value, start, end) 的时间窗口应包含两个端点，结束时刻的记录被遗漏。参数为整数时间戳。

任务 `4d830923189f` · 状态 `completed` · 模式 `live_baseline`

仓库 `fixture/inclusive-window` · 缺陷版本 `a6d9cd52f42a2113ec00c1df75636a1dec1cd3eb`

验收修复版本 `558e0fc0427d31f60a0d5504c31f04a3019d7a3c`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `2cbd1734de38a869b3dd9c5ebd3bba62c3733278ea72cd9f08520d14ed11c701`

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
  "input_tokens": 400,
  "output_tokens": 187,
  "estimated_cost_cny": 0.002756,
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
