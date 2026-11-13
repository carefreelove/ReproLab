# ReproLab 复现报告

source.paginate(items, offset, limit) 应拒绝负 offset，抛出 ValueError。当前负数会按 Python 切片规则处理。

任务 `56f1b60a5bdd` · 状态 `completed` · 模式 `live_baseline`

仓库 `fixture/negative-offset` · 缺陷版本 `7e9693919934deaea9ba339b5ceff1813c75f1b3`

验收修复版本 `b887e9c2c27c831b6de542a586ce1fa022700a7e`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `232ed5adcd9ec2d23f6ff73f1c9e7f72cac92c368e14429799b8e727f691f354`

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
  "input_tokens": 402,
  "output_tokens": 96,
  "estimated_cost_cny": 0.001887,
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
