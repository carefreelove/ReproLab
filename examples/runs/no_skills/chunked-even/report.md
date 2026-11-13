# ReproLab 复现报告

more_itertools.chunked_even(iterable, n) 在 n=0 时应得到空结果且不消耗输入迭代器；n<0 时应抛出 ValueError 且不消耗输入。请验证边界及迭代器状态。

任务 `291573a1fc5d` · 状态 `completed` · 模式 `live`

仓库 `more-itertools/more-itertools` · 缺陷版本 `20c4ee5c63f8f8c35a37aee3b69d95cd2450c09a`

验收修复版本 `08dca284ba5446a026afdc34067b658f9da989eb`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `1ef1be789bee44334406f68836112c04b184f51df31207464e89e0ce56fa3c54`

## 使用的 Skills


## 计划与假设

```json
{
  "plan": [
    {
      "task": "定位 more_itertools.chunked_even 实现与相关测试",
      "status": "done",
      "evidence": [
        "ar-b8b6f302f4e3ae08fc24",
        "ar-da0301c61bc6b2013616"
      ]
    },
    {
      "task": "分析 n=0 / n<0 边界行为与迭代器消耗情况",
      "status": "done",
      "evidence": [
        "ar-9bf8ba7e07ca7cdbcde9"
      ]
    },
    {
      "task": "编写复现测试并运行，验证真实错误类别",
      "status": "done",
      "evidence": [
        "ar-9bf8ba7e07ca7cdbcde9",
        "ar-68aa0c2564bbf33170c4"
      ]
    },
    {
      "task": "提交复现结果",
      "status": "in_progress",
      "evidence": []
    }
  ],
  "hypotheses": [
    {
      "id": "h1",
      "claim": "chunked_even 缺少 n<=0 校验：n=0 时 min_buffer=2 预取 2 个元素，随后 islice(..., 0, None, 0) 抛 ValueError（step 必须为正）；n<0 时 min_buffer 为正数，预取全部 5 个元素，且不抛 ValueError（无异常，返回空）。",
      "expected": "n=0 应返回 [] 且 items_seen==0；n=-1/-2 应抛 ValueError 且 items_seen==0。实测：n=0 抛 ValueError（islice step），n<0 无异常且 items_seen==5。",
      "status": "supported",
      "evidence": [
        "ar-9bf8ba7e07ca7cdbcde9"
      ],
      "next_action": "假设已支持（三个测试均因边界未校验而失败），提交复现。"
    }
  ]
}
```

## 实验

- `ex-3e6223171695` · 假设 `h1` · assertion_failure · 日志 `ar-9bf8ba7e07ca7cdbcde9`

## 调用统计

```json
{
  "model_calls": 9,
  "input_tokens": 59967,
  "output_tokens": 1810,
  "estimated_cost_cny": 0.1613,
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
