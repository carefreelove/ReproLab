# ReproLab 复现报告

source.Bucket 的不同实例应拥有独立的 items 列表。调用 add(value) 后另一个实例也出现了数据。

任务 `120d19458e27` · 状态 `completed` · 模式 `live`

仓库 `fixture/shared-state` · 缺陷版本 `76bd021083c1d479ddea1694a62cb2fd82fa4433`

验收修复版本 `fd9adfe6843405e6b6a8e59204702f2bfa71d233`

## 验收结果

**verified**。同一测试在缺陷版稳定失败，在修复版全部通过

测试 SHA256 `9859084651fa35e72bc8894867c4d68ca322219f66c1c7812708ac9d68475c2d`

## 使用的 Skills

- `iterator-state` · 问题为实例间可变状态共享（items 列表），属于实例状态共享类缺陷 · 内容 `b2d1abe2adbea8f63d480510c1f0d68f964f4e0362e852c74b3add61b8ec1164`

## 计划与假设

```json
{
  "plan": [
    {
      "task": "定位 source.Bucket 实现，确认 items 列表定义方式",
      "status": "done",
      "evidence": [
        "ar-2af5a23e11ad64ba7a1a"
      ]
    },
    {
      "task": "构造两实例独立性的 pytest 复现测试",
      "status": "done",
      "evidence": [
        "ar-c8627c219e1c99e6dc40"
      ]
    },
    {
      "task": "运行测试验证缺陷并提交复现",
      "status": "done",
      "evidence": [
        "ar-d160d28fbfe848cffeec"
      ]
    }
  ],
  "hypotheses": [
    {
      "id": "h1",
      "claim": "Bucket.items 为类属性列表，add() 通过 self.items.append 修改类级列表，导致所有实例共享同一列表",
      "expected": "两实例独立时 b2.items 应为空；实际 b2.items == ['a']，且跨测试残留 ['a', 1, 2]",
      "status": "supported",
      "evidence": [
        "ar-2af5a23e11ad64ba7a1a",
        "ar-c8627c219e1c99e6dc40",
        "ar-d160d28fbfe848cffeec"
      ],
      "next_action": "行为已触发，提交复现"
    }
  ]
}
```

## 实验

- `ex-73d68aff34a2` · 假设 `h1` · assertion_failure · 日志 `ar-c8627c219e1c99e6dc40`

## 调用统计

```json
{
  "model_calls": 8,
  "input_tokens": 34874,
  "output_tokens": 1240,
  "estimated_cost_cny": 0.095604,
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
