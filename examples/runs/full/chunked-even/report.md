# ReproLab 复现报告

more_itertools.chunked_even(iterable, n) 在 n=0 时应得到空结果且不消耗输入迭代器；n<0 时应抛出 ValueError 且不消耗输入。请验证边界及迭代器状态。

任务 `0e56a62a0d0b` · 状态 `completed` · 模式 `live`

仓库 `more-itertools/more-itertools` · 缺陷版本 `20c4ee5c63f8f8c35a37aee3b69d95cd2450c09a`

验收修复版本 `08dca284ba5446a026afdc34067b658f9da989eb`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `4593758fb1157f3f5df0bb2e398c8c1d17b67f34715ccc081333e5fa9c355395`

## 使用的 Skills

- `boundary-analysis` · 任务核心是 n=0 与 n<0 的边界行为 · 内容 `9fdd5d488abcb74e2bbf0fcbe0ae89363135a7af187052c509d8c5a928a04e53`
- `iterator-state` · 需验证不消耗输入迭代器 · 内容 `b2d1abe2adbea8f63d480510c1f0d68f964f4e0362e852c74b3add61b8ec1164`

## 计划与假设

```json
{
  "plan": [
    {
      "task": "定位 more_itertools.chunked_even 实现与现有测试",
      "status": "done",
      "evidence": [
        "ar-8f3c146f9ab8c03952c2",
        "ar-c0ff09eaee37996ee58a"
      ]
    },
    {
      "task": "激活 boundary-analysis 与 iterator-state 技能，明确边界与迭代器消耗验证方法",
      "status": "done",
      "evidence": []
    },
    {
      "task": "编写参数化复现测试：n=0 空结果不消耗、n<0 抛 ValueError 不消耗",
      "status": "done",
      "evidence": []
    },
    {
      "task": "运行测试并依据真实错误类别更新假设",
      "status": "done",
      "evidence": [
        "ar-9e47873adc1ca239c979"
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
      "claim": "n=0 时 min_buffer=2 先消耗 2 个元素，随后 islice(..., 0, None, 0) 抛 ValueError（step 非正），而非返回空结果；n<0 时 min_buffer 为正，先消耗 min_buffer 个元素（n=-1 消耗 6，n=-2/-5 消耗 7），之后才抛 ValueError。即两个边界都违反“不消耗输入”契约。",
      "expected": "n=0 返回 [] 且 consumed==0；n<0 抛 ValueError 且 consumed==0。",
      "status": "supported",
      "evidence": [
        "ar-9e47873adc1ca239c979"
      ],
      "next_action": "假设已被日志支持（4 个目标失败，正常 n=3 基线通过），提交复现。"
    }
  ]
}
```

## 实验

- `ex-95216b109938` · 假设 `h1` · target_exception · 日志 `ar-9e47873adc1ca239c979`

## 调用统计

```json
{
  "model_calls": 9,
  "input_tokens": 72067,
  "output_tokens": 2301,
  "estimated_cost_cny": 0.195055,
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
