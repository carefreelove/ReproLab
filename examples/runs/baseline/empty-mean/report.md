# ReproLab 复现报告

source.mean([]) 应返回 0，非空输入返回算术平均值。当前空列表会失败，请生成测试。

任务 `b50f31f7f80e` · 状态 `completed` · 模式 `live_baseline`

仓库 `fixture/empty-mean` · 缺陷版本 `0bb06820d5dbd4aeeba094a435744772a2a76f51`

验收修复版本 `50a825ee574abf95dd1ba5bb3a70bbb55a7fd307`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `d4a82066636a0296a821ef04dcabe9154d3984bd5657da51da9bcf6645307d91`

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
  "input_tokens": 394,
  "output_tokens": 113,
  "estimated_cost_cny": 0.002031,
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
