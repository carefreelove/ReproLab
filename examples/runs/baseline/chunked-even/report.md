# ReproLab 复现报告

more_itertools.chunked_even(iterable, n) 在 n=0 时应得到空结果且不消耗输入迭代器；n<0 时应抛出 ValueError 且不消耗输入。请验证边界及迭代器状态。

任务 `91d2caae0f70` · 状态 `completed` · 模式 `live_baseline`

仓库 `more-itertools/more-itertools` · 缺陷版本 `20c4ee5c63f8f8c35a37aee3b69d95cd2450c09a`

验收修复版本 `08dca284ba5446a026afdc34067b658f9da989eb`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `6f08b2f74d37dd26e2c8f437038bfc910918a16d40936bed297c78c2b31d5b5c`

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
  "input_tokens": 3711,
  "output_tokens": 305,
  "estimated_cost_cny": 0.011835,
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
