# ReproLab 复现报告

more_itertools.chunked_even(iterable, n) 在 n=0 时应得到空结果且不消耗输入迭代器；n<0 时应抛出 ValueError 且不消耗输入。请验证边界及迭代器状态。

任务 `e3c9fd453b5c` · 状态 `completed` · 模式 `live`

仓库 `more-itertools/more-itertools` · 缺陷版本 `20c4ee5c63f8f8c35a37aee3b69d95cd2450c09a`

验收修复版本 `08dca284ba5446a026afdc34067b658f9da989eb`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `1d88b32412512378276a202d1bdc4114914e1a5a35228c96b847db678856fd70`

## 使用的 Skills

- `boundary-analysis` · 需要验证 n=0 与 n<0 边界行为 · 内容 `9fdd5d488abcb74e2bbf0fcbe0ae89363135a7af187052c509d8c5a928a04e53`
- `iterator-state` · 需要验证 n=0/n<0 时不消耗输入迭代器 · 内容 `b2d1abe2adbea8f63d480510c1f0d68f964f4e0362e852c74b3add61b8ec1164`

## 计划与假设

```json
{
  "plan": [
    {
      "task": "定位 chunked_even 实现与相关测试",
      "status": "done",
      "evidence": [
        "ar-fa0d0079107c40c5d318"
      ]
    },
    {
      "task": "激活 boundary-analysis 与 iterator-state 技能，明确边界与迭代器消耗验证方法",
      "status": "done",
      "evidence": [
        "ar-da0301c61bc6b2013616"
      ]
    },
    {
      "task": "编写复现测试：n=0 空结果且不消耗；n<0 抛 ValueError 且不消耗",
      "status": "done",
      "evidence": []
    },
    {
      "task": "运行测试并依据失败细节调整",
      "status": "done",
      "evidence": [
        "ar-23de8c151c25510e3584",
        "ar-f858762167b094290147"
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
      "claim": "chunked_even 在 n=0 时 min_buffer=(0-1)*(0-2)=2，会先 islice 消耗 2 个输入项，随后 islice(..., 0, None, 0) 抛 ValueError（step 必须为正）；即 n=0 既不返回空结果，也消耗了输入迭代器。",
      "expected": "n=0 时抛 ZeroDivisionError 且 consumed==2；实际抛 ValueError 且输入被消耗。",
      "status": "supported",
      "evidence": [
        "ar-23de8c151c25510e3584"
      ],
      "next_action": "已由测试确认：n=0 抛 ValueError（islice step=0）且输入被消耗；假设支持，提交复现。"
    },
    {
      "id": "h2",
      "claim": "chunked_even 在 n<0 时 min_buffer=(n-1)*(n-2)>0，会先 islice 消耗输入项，之后 islice(..., n, None, n) 对负 step 抛 ValueError，但此时输入已被消耗，违反“抛 ValueError 且不消耗输入”。",
      "expected": "n<0 时抛 ValueError 且 consumed==0；实际 consumed==5（全部输入被 min_buffer 的 islice 消耗）。",
      "status": "supported",
      "evidence": [
        "ar-23de8c151c25510e3584"
      ],
      "next_action": "已确认：n=-1/-2/-5 均抛 ValueError 但先消耗了全部 5 个元素，违反“不消耗输入”。提交复现。"
    }
  ]
}
```

## 实验

- `ex-f62411ab8382` · 假设 `h2` · target_exception · 日志 `ar-23de8c151c25510e3584`

## 调用统计

```json
{
  "model_calls": 10,
  "input_tokens": 79594,
  "output_tokens": 3071,
  "estimated_cost_cny": 0.22051,
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
