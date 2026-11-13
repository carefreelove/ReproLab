# ReproLab 复现报告

source.chunks(items, n) 返回分块列表。约定 n=0 返回空列表，n<0 抛出 ValueError。当前零容量失败。

任务 `40554a8d863c` · 状态 `completed` · 模式 `live_baseline`

仓库 `fixture/zero-capacity` · 缺陷版本 `387999a3392af7c4baf1b9d98433308e85bb7a33`

验收修复版本 `7be14f48646d64dc13bba72eefbcce92464fab1c`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `7706ada1b314150c8f212cdbe63c9d4ca984cc4411316683ef2079b52b1a22c1`

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
  "input_tokens": 415,
  "output_tokens": 140,
  "estimated_cost_cny": 0.00234,
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
